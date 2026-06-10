#!/usr/bin/env python3
"""PHDWin-to-ARIES table builder.

Scope: reads a PHDWin review SQLite (PHD_MAINLSE, PHD_OWNER, PHD_MONHIST, etc.)
and produces resolved ARIES-named tables (AC_PROPERTY, AC_PRODUCT, AC_ECONOMIC,
AC_SCENARIO, AC_SETUP, AC_OWNER, PROJECT, PROJLIST, ...).  Output is handed to
the shared aries_writer for CSV, SQLite, and Access serialisation.

No ARIES file-format logic lives here; this module only maps PHDWin semantics
to ARIES column names and value conventions.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

from aries_economic import build_ac_economic_rows


# ---------------------------------------------------------------------------
# Load the shared ARIES writer from areas/aries/lib/aries_writer.py.
# ---------------------------------------------------------------------------

def _load_shared_aries_writer() -> ModuleType:
    writer_path = Path(__file__).resolve().parents[5] / "areas" / "aries" / "lib" / "aries_writer.py"
    spec = importlib.util.spec_from_file_location("tauris_aries_writer", writer_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load shared Aries writer from {writer_path}")
    cached = sys.modules.get(spec.name)
    if cached is not None:
        return cached
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_aries_writer = _load_shared_aries_writer()

# Re-export shared writer API used by callers of this module.
EXPORT_TABLE_ORDER = _aries_writer.EXPORT_TABLE_ORDER
PER_LEASE_TABLES = _aries_writer.PER_LEASE_TABLES
GLOBAL_TABLES = _aries_writer.GLOBAL_TABLES
write_csv_tables = _aries_writer.write_csv_tables
write_aries_sqlite_tables = _aries_writer.write_aries_sqlite_tables
read_aries_sqlite_tables = _aries_writer.read_aries_sqlite_tables
resolve_access_template_path = _aries_writer.resolve_access_template_path
prepare_access_tables = _aries_writer.prepare_access_tables
is_review_economic_row = _aries_writer.is_review_economic_row
write_access_database_with_defaults = _aries_writer.write_access_database_with_defaults

DEFAULT_DBSKEY = "168888"
DEFAULT_PROJECT_KEY = "00_RSV_CAT"
DEFAULT_SCENARIO_NAME = "ACTIVE"
DEFAULT_DATA_QUALIFIER = "TAURIS"
DEFAULT_REVIEW_QUALIFIER = "PY_REVIEW"


@dataclass
class AriesExportResult:
    source_sqlite: Path
    output_dir: Path
    csv_dir: Path
    accdb_path: Path | None
    table_counts: dict[str, int]
    warnings: list[str]
    diagnostics: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "sourceSqlite": str(self.source_sqlite),
            "outputDir": str(self.output_dir),
            "csvDir": str(self.csv_dir),
            "accdbPath": str(self.accdb_path) if self.accdb_path else None,
            "tableCounts": self.table_counts,
            "warnings": self.warnings,
        }
        if self.diagnostics is not None:
            result["diagnostics"] = self.diagnostics
        return result


def row_get(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    by_upper = {str(k).upper(): v for k, v in row.items()}
    for name in names:
        if name.upper() in by_upper:
            value = by_upper[name.upper()]
            return default if value is None else value
    return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value))
    except (TypeError, ValueError):
        return default


def clean_text(value: Any, max_len: int | None = None) -> str:
    text = "" if value is None else str(value).strip()
    text = " ".join(text.split())
    if max_len is not None:
        return text[:max_len]
    return text


def sanitize_key(value: Any, max_len: int = 9) -> str:
    text = clean_text(value).upper()
    result = "".join(ch for ch in text if ch.isalnum() or ch == "_")
    return (result or "GROUP")[:max_len]


def friendly_source_name(path: Path) -> str:
    stem = re.sub(r"[-_]\d{4}-\d{2}-\d{2}$", "", path.stem)
    name = re.sub(r"[^0-9A-Za-z]+", "_", stem).strip("_")
    return name or "SOURCE"


def propnum_for_lease(lease_id: int) -> str:
    return f"PHD{lease_id:06d}"


def special_propnum(case_type_name: str, lease_id: int) -> str:
    prefix = (clean_text(case_type_name) or "CASE")[:4].upper().ljust(4, "X")
    return f"{prefix}{lease_id:06d}"


def aries_key(propnum: str) -> str:
    return f"DBSKEY='{DEFAULT_DBSKEY}' AND PROPNUM='{propnum}'"


def clarion_date_to_date(value: Any) -> date | None:
    serial = to_int(value, default=-1)
    if serial < 0:
        return None
    return date(1800, 12, 28) + timedelta(days=serial)


def parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            pass
    return clarion_date_to_date(value)


def aries_date(value: Any) -> str:
    parsed = parse_date(value)
    return parsed.strftime("%Y.%m.%d") if parsed else ""


def monthly_value(row: dict[str, Any], product_index: int, month: int) -> float:
    zero_based = month - 1
    return to_float(row_get(
        row,
        f"PROD{product_index}${month}",
        f"PROD{product_index}_{zero_based}",
        f"PROD{product_index}{zero_based}",
        f"PROD{product_index}_{month}",
        f"PROD{product_index}{month}",
        default=0,
    ))


def aries_owner_start_date(value: Any) -> str:
    if to_int(value, default=0) <= 0:
        return "2000.01.01"
    return aries_date(value) or "2000.01.01"


def month_end(year: int, month: int) -> str:
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return end.strftime("%Y.%m.%d")


def open_sqlite(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND upper(name) = upper(?)",
        (table,),
    ).fetchone()
    return row is not None


def read_table(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    if not table_exists(conn, table):
        return []
    rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
    return [dict(row) for row in rows]


def read_table_filtered(
    conn: sqlite3.Connection,
    table: str,
    lease_ids: list[int] | None,
) -> list[dict[str, Any]]:
    if not table_exists(conn, table):
        return []
    if not lease_ids:
        rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
    else:
        placeholders = ",".join("?" for _ in lease_ids)
        rows = conn.execute(
            f'SELECT * FROM "{table}" WHERE LSE_ID IN ({placeholders})',
            lease_ids,
        ).fetchall()
    return [dict(row) for row in rows]


def indexed(rows: Iterable[dict[str, Any]], key: str) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        result[to_int(row_get(row, key))] = row
    return result


def build_category_name(category: dict[str, Any] | None, fallback: Any) -> str:
    if category:
        return clean_text(row_get(category, "SHORTNAME", "SHORT_NAME", default="")) or clean_text(row_get(category, "NAME", default=""))
    return str(fallback)


def build_class_name(cls: dict[str, Any] | None, fallback: Any) -> str:
    if cls:
        return clean_text(row_get(cls, "SHORTNAME", "SHORT_NAME", default="")) or clean_text(row_get(cls, "NAME", default=""))
    return str(fallback)


def case_type_name(lease: dict[str, Any]) -> str:
    explicit = clean_text(row_get(lease, "CASETYPENAME", "CASE_TYPE_NAME", default=""))
    if explicit:
        return explicit
    code = to_int(row_get(lease, "CASETYPE", "CASE_TYPE", default=0))
    return {
        3: "UNIT",
        6: "UNIT",
        9: "INCR",
    }.get(code, "CASE")


def build_project_membership(
    leases: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    list_rows: list[dict[str, Any]],
    owners: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
) -> dict[int, list[dict[str, Any]]]:
    leases_by_id = {to_int(row_get(lease, "LSE_ID")): lease for lease in leases}
    memberships: dict[int, list[dict[str, Any]]] = {}
    seen: set[tuple[int, int]] = set()
    group_ids_with_list_rows = {to_int(row_get(row, "GRP_ID")) for row in list_rows}

    def add(group_id: int, lease_id: int) -> None:
        if selected_lease_ids is not None and lease_id not in selected_lease_ids:
            return
        if (group_id, lease_id) in seen:
            return
        lease = leases_by_id.get(lease_id)
        if lease is None:
            return
        seen.add((group_id, lease_id))
        memberships.setdefault(group_id, []).append(lease)

    for row in sorted(list_rows, key=lambda r: (to_int(row_get(r, "GRP_ID")), to_int(row_get(r, "LSE_ID")))):
        add(to_int(row_get(row, "GRP_ID")), to_int(row_get(row, "LSE_ID")))

    for row in sorted(owners, key=lambda r: (to_int(row_get(r, "GRP_ID")), to_int(row_get(r, "LSE_ID")))):
        group_id = to_int(row_get(row, "GRP_ID"))
        if group_id in group_ids_with_list_rows:
            continue
        if to_int(row_get(row, "SEQ"), default=1) != 1:
            continue
        add(group_id, to_int(row_get(row, "LSE_ID")))

    return memberships


def is_all_cases_group(group: dict[str, Any]) -> bool:
    return clean_text(row_get(group, "GRP_DESC", "GROUP_NAME", "NAME", default="")).lower() == "all cases"


def group_description(group: dict[str, Any]) -> str:
    return clean_text(row_get(group, "GRP_DESC", "GROUP_NAME", "NAME", default=f"Group {row_get(group, 'GRP_ID')}"))


def group_qualifier(group: dict[str, Any]) -> str:
    return clean_text(row_get(group, "QUALIFIER", "QUAL", default=group_description(group))) or group_description(group)


def project_key(group: dict[str, Any]) -> str:
    return f"{sanitize_key(group_qualifier(group), 9)}{to_int(row_get(group, 'GRP_ID'))}"


def owner_name_for_group(group: dict[str, Any] | None, group_id: int) -> str:
    if not group:
        return f"GRP{group_id}"[:12]
    return sanitize_key(group_description(group), 12)


def build_aries_tables(source_sqlite: Path, lease_ids: list[int] | None = None) -> tuple[dict[str, list[dict[str, Any]]], list[str], dict[str, Any]]:
    warnings: list[str] = []
    with open_sqlite(source_sqlite) as conn:
        titles = read_table(conn, "PHD_TITLES")
        leases = read_table(conn, "PHD_MAINLSE")
        product_names = read_table(conn, "PHD_PRODUCTNAMES")
        owners = read_table(conn, "PHD_OWNER")
        groups = read_table(conn, "PHD_GROUPS")
        list_rows = read_table(conn, "PHD_LIST")
        classes = read_table(conn, "PHD_CLASS")
        categories = read_table(conn, "PHD_CATEGORY")
        monhist = read_table_filtered(conn, "PHD_MONHIST", lease_ids)
        daily = read_table_filtered(conn, "PHD_DAILY", lease_ids)
        economic_source_tables = {
            "PHD_MAINLSE": leases,
            "PHD_PRODUCTNAMES": product_names,
            "PHD_OWNER": owners,
            "PHD_FORCAST": read_table_filtered(conn, "PHD_FORCAST", lease_ids),
            "PHD_LSESEGMENT": read_table_filtered(conn, "PHD_LSESEGMENT", lease_ids),
            "PHD_LSEPRODVAL": read_table_filtered(conn, "PHD_LSEPRODVAL", lease_ids),
            "PHD_ECON": read_table_filtered(conn, "PHD_ECON", lease_ids),
            "PHD_INVEST": read_table_filtered(conn, "PHD_INVEST", lease_ids),
            "PHD_INVESTDESCR": read_table(conn, "PHD_INVESTDESCR"),
            "PHD_CUMVOL": read_table_filtered(conn, "PHD_CUMVOL", lease_ids),
            "MOD_SCEN": read_table(conn, "MOD_SCEN"),
            "MOD_TEMPLATE": read_table(conn, "MOD_TEMPLATE"),
        }

    if not leases:
        raise ValueError("PHD_MAINLSE is required to build Aries export tables.")

    selected_lease_ids = set(lease_ids or [])
    if selected_lease_ids:
        leases = [lease for lease in leases if to_int(row_get(lease, "LSE_ID")) in selected_lease_ids]
        if not leases:
            raise ValueError("No PHD_MAINLSE rows matched the requested lease ids.")
    else:
        selected_lease_ids = None  # type: ignore[assignment]

    product_by_code = indexed(product_names, "PRODUCTCODE")
    class_by_id = indexed(classes, "CLA_ID")
    category_by_id = indexed(categories, "CAT_ID")
    group_by_id = indexed(groups, "GRP_ID")
    leases_by_id = {to_int(row_get(lease, "LSE_ID")): lease for lease in leases}
    memberships = build_project_membership(leases, groups, list_rows, owners, selected_lease_ids)
    source_db = friendly_source_name(source_sqlite)

    ac_property: list[dict[str, Any]] = []
    for lease in sorted(leases, key=lambda r: to_int(row_get(r, "LSE_ID"))):
        lease_id = to_int(row_get(lease, "LSE_ID"))
        product = product_by_code.get(to_int(row_get(lease, "MAJOR_PHASE", "MAJORPHASE", default=0)))
        reserve_class_id = to_int(row_get(lease, "RSV_CLASS", default=0))
        reserve_category_id = to_int(row_get(lease, "PDP_CATEGORY", "RSV_CATEGORY", default=0))
        reserve_class = build_class_name(class_by_id.get(reserve_class_id), reserve_class_id)
        reserve_category = build_category_name(category_by_id.get(reserve_category_id), reserve_category_id)
        partner_names = sorted({
            group_description(group)
            for owner in owners
            for group in groups
            if to_int(row_get(owner, "LSE_ID")) == lease_id
            and to_int(row_get(owner, "SEQ"), default=1) == 1
            and to_int(row_get(owner, "GRP_ID")) == to_int(row_get(group, "GRP_ID"))
        })

        prod_start = aries_date(row_get(lease, "SOP_DTTM", "SOP_DATE", "SOP", default=""))
        ac_property.append({
            "DBSKEY": DEFAULT_DBSKEY,
            "PROPNUM": propnum_for_lease(lease_id),
            "SRC_DB": source_db,
            "SEQ": lease_id,
            "SEQNUM": lease_id,
            "MAJOR": clean_text(row_get(product or {}, "DESCR", "DESCRIPTION", default="")),
            "PRIOR_OIL": 0,
            "PRIOR_GAS": 0,
            "PRIOR_WTR": 0,
            "CLASS": reserve_class,
            "RSV_CLASS": reserve_class_id,
            "RSV_CLASS_ID": reserve_class_id,
            "RSV_CLASS_NAME": reserve_class,
            "RSV_CATEGORY": reserve_category_id,
            "RSV_CATEGORY_ID": reserve_category_id,
            "RSV_CATEGORY_NAME": reserve_category,
            "RSV_CAT": reserve_category,
            "RESCAT": reserve_category,
            "RSC_SORT": f"{reserve_class_id - 1}{reserve_category_id}",
            "FIELD": clean_text(row_get(lease, "FLD", "FIELD", default="")),
            "RESERVOIR": clean_text(row_get(lease, "RESERVOIR", default="")),
            "LEASE": clean_text(row_get(lease, "LSE_NAME", "LEASE", default="")),
            "CASE_NAME": clean_text(row_get(lease, "LSE_NAME", "LEASE", default="")),
            "COUNTY": clean_text(row_get(lease, "COUNTY", default="")),
            "STATE": clean_text(row_get(lease, "STATE", default="")),
            "COUNTRY": clean_text(row_get(lease, "COUNTRY", default="")),
            "OPERATOR": clean_text(row_get(lease, "OPER", "OPERATOR", default="")),
            "WELL": clean_text(row_get(lease, "WELL", default="")),
            "LSE_ID": lease_id,
            "CASETYPE": case_type_name(lease),
            "PARTNERS": ";".join(partner_names),
            "WELLTYPE": clean_text(row_get(lease, "WELLTYPE", default="")),
            "GASGATH": clean_text(row_get(lease, "GASGATH", default="")),
            "OILGATH": clean_text(row_get(lease, "OILGATH", default="")),
            "PROD_START": prod_start,
            "FIRST_PROD": prod_start,
            "PROD_END": aries_date(row_get(lease, "EOP_DTTM", "EOP_DATE", "EOP", default="")),
            "DATE_COMP": aries_date(row_get(lease, "COMP_DTTM", "COMP_DATE", "COMPLETION_DATE", default="")),
            "DEPTH": to_float(row_get(lease, "TD", "DEPTH", default=0)),
            "LATITUDE": to_float(row_get(lease, "LAT", "LATITUDE", default=0)),
            "LONGITUDE": to_float(row_get(lease, "LONG", "LONGITUDE", default=0)),
            "LOCATION": clean_text(row_get(lease, "LOCATION", default="")),
            "GRADIENT": to_float(row_get(lease, "GRADIENT", default=0)),
            "TUBINGDIAM": to_float(row_get(lease, "TUBINGID", "TUBINGDIAM", default=0)),
            "TAI_EXCLUDE": "1" if to_int(row_get(lease, "EXCLSUM", default=0)) == 1 else "",
            "EXCLSUM": "true" if to_int(row_get(lease, "EXCLSUM", default=0)) == 1 else "false",
            "EXCLCASH": "true" if to_int(row_get(lease, "EXCLCASH", default=0)) == 1 else "false",
            "EXCLVOL": "true" if to_int(row_get(lease, "EXCLVOL", default=0)) == 1 else "false",
            # Standard ARIES identification columns
            "API": clean_text(row_get(lease, "API", "API_NUM", default="")),
            "UWI": clean_text(row_get(lease, "UWI", default="")),
            "WELL_ID": clean_text(row_get(lease, "WELL_ID", default="")),
            "STATUS": clean_text(row_get(lease, "STATUS", "WELL_STATUS", default="")),
            "CODE": "",
            # Standard ARIES geographic columns
            "AREA": clean_text(row_get(lease, "AREA", "BASIN", default="")),
            "DIVISION": clean_text(row_get(lease, "DIVISION", default="")),
            "REGION": clean_text(row_get(lease, "REGION", default="")),
            # Standard ARIES engineering columns
            "LOE": to_float(row_get(lease, "LOE", default=0)),
            "BTU": to_float(row_get(lease, "BTU", default=0)),
            "LIQ_GRAV": to_float(row_get(lease, "LIQ_GRAV", "API_GRAV", default=0)),
            "GAS_GRAV": to_float(row_get(lease, "GAS_GRAV", default=0)),
            "TEMP_BH": to_float(row_get(lease, "TEMP_BH", "BHT", default=0)),
            "PB_DEPTH": to_float(row_get(lease, "PB_DEPTH", default=0)),
            "UPR_PERF": to_float(row_get(lease, "UPR_PERF", default=0)),
            "LWR_PERF": to_float(row_get(lease, "LWR_PERF", default=0)),
        })

    ac_product: list[dict[str, Any]] = []
    for row in monhist:
        lease_id = to_int(row_get(row, "LSE_ID"))
        if lease_id not in leases_by_id or to_int(row_get(row, "TYPE"), default=0) != 0:
            continue
        year = to_int(row_get(row, "YEAR"))
        if year <= 0:
            continue
        for month in range(1, 13):
            ac_product.append({
                "PROPNUM": propnum_for_lease(lease_id),
                "P_DATE": month_end(year, month),
                "OIL": monthly_value(row, 2, month),
                "GAS": monthly_value(row, 1, month),
                "WATER": monthly_value(row, 3, month),
                "WELLCOUNT": monthly_value(row, 4, month),
                "DAYS_ON": monthly_value(row, 5, month),
            })

    ac_test: list[dict[str, Any]] = []
    for row in daily:
        lease_id = to_int(row_get(row, "LSE_ID"))
        if lease_id not in leases_by_id or to_int(row_get(row, "TYPE"), default=0) != 0:
            continue
        ac_test.append({
            "PROPNUM": propnum_for_lease(lease_id),
            "DATE": aries_date(row_get(row, "TDATE_DTTM", "TDATE", "DATE", default="")),
            "OIL_RATE": to_float(row_get(row, "BBLDAY", "OIL_RATE", default=0)),
            "GAS_RATE": to_float(row_get(row, "MCFDAY", "GAS_RATE", default=0)),
            "WATER_RATE": to_float(row_get(row, "WATDAY", "WATER_RATE", default=0)),
            "CASINGPRESSURE": to_float(row_get(row, "CSGPRES", "CASINGPRESSURE", default=0)),
            "TUBINGPRESSURE": to_float(row_get(row, "FTP", "TUBINGPRESSURE", default=0)),
            "BHPZ": to_float(row_get(row, "BHPZ", default=0)),
            "SIBHP": to_float(row_get(row, "SIBHP", default=0)),
            "SITP": to_float(row_get(row, "SITP", default=0)),
            "CHOKE": to_float(row_get(row, "CHOKESIZE", "CHOKE", default=0)),
            "Z_FACTOR": to_float(row_get(row, "ZFACTOR", "Z_FACTOR", default=0)),
            "NOTES": clean_text(row_get(row, "NOTES", default="")),
        })

    ac_owner: list[dict[str, Any]] = []
    seen_owner_keys: set[tuple[str, str, str, str, str]] = set()

    def add_owner_row(owner_row: dict[str, Any], phase_name: str, interest: float) -> None:
        if interest == 0:
            return
        lease_id = to_int(row_get(owner_row, "LSE_ID"))
        if lease_id not in leases_by_id:
            return
        group_id = to_int(row_get(owner_row, "GRP_ID"))
        group = group_by_id.get(group_id)
        scenario = DEFAULT_SCENARIO_NAME if group is None or is_all_cases_group(group) else group_qualifier(group)
        start_date = aries_owner_start_date(row_get(owner_row, "RESOLVEDDATE", default=0))
        owner_name = owner_name_for_group(group, group_id)
        key = (propnum_for_lease(lease_id), scenario, phase_name, start_date, owner_name)
        if key in seen_owner_keys:
            return
        seen_owner_keys.add(key)
        ac_owner.append({
            "PROPNUM": key[0],
            "SCENARIO": scenario,
            "PHASENAME": phase_name,
            "STARTDATE": start_date,
            "HISTORY": "E",
            "OWNERNAME": owner_name,
            "UNITS": "N",
            "INTEREST": interest,
        })

    for row in sorted(owners, key=lambda r: (to_int(row_get(r, "LSE_ID")), to_int(row_get(r, "GRP_ID")), to_int(row_get(r, "SEQ"), default=1))):
        lease_id = to_int(row_get(row, "LSE_ID"))
        if selected_lease_ids is not None and lease_id not in selected_lease_ids:
            continue
        working_interest = to_float(row_get(row, "WRKINT", default=0))
        net_revenue_interest = to_float(row_get(row, "LSENRI", "REVINT", default=0))
        add_owner_row(row, "LSE/WI", working_interest)
        add_owner_row(row, "NET/OIL", net_revenue_interest)
        add_owner_row(row, "NET/GAS", net_revenue_interest)

    project_rows = [{
        "DBSKEY": DEFAULT_DBSKEY,
        "PROJKEY": DEFAULT_PROJECT_KEY,
        "NAME": "All Cases",
        "OWNER": "admin",
        "PBLIC": "Y",
        "DESCRIPTN": "Default / All Cases",
        "QUERY": ".",
        "REBUILD": "R",
        "PROP_DEL": "N",
        "SHOWID_CHNG": "N",
    }]
    for group in sorted(groups, key=lambda g: to_int(row_get(g, "GRP_ID"))):
        group_id = to_int(row_get(group, "GRP_ID"))
        if is_all_cases_group(group) or group_id not in memberships:
            continue
        project_rows.append({
            "DBSKEY": DEFAULT_DBSKEY,
            "PROJKEY": project_key(group),
            "NAME": clean_text(group_description(group), 30),
            "OWNER": "admin",
            "PBLIC": "Y",
            "DESCRIPTN": group_description(group),
            "QUERY": ".",
            "REBUILD": "R",
            "PROP_DEL": "N",
            "SHOWID_CHNG": "N",
        })

    projlist: list[dict[str, Any]] = []
    seq_by_project: dict[str, int] = {}

    def add_projlist(projkey: str, lease: dict[str, Any], scenario: str = "") -> None:
        lease_id = to_int(row_get(lease, "LSE_ID"))
        seq_by_project[projkey] = seq_by_project.get(projkey, 0) + 1
        propnum = propnum_for_lease(lease_id)
        projlist.append({
            "INTKEY": aries_key(propnum),
            "PROJKEY": projkey,
            "PROPKEY": aries_key(propnum),
            "PROPNAME": clean_text(row_get(lease, "LSE_NAME", default=propnum)),
            "ENTITYTYPE": "Property",
            "SELECTED": "Y",
            "BREAKLEVEL": 0,
            "PROJSEQ": seq_by_project[projkey],
            "MAJOR": "",
            "SCENARIO": scenario,
        })

    for lease in sorted(leases, key=lambda r: to_int(row_get(r, "LSE_ID"))):
        add_projlist(DEFAULT_PROJECT_KEY, lease)
    for group in sorted(groups, key=lambda g: to_int(row_get(g, "GRP_ID"))):
        group_id = to_int(row_get(group, "GRP_ID"))
        if is_all_cases_group(group) or group_id not in memberships:
            continue
        for lease in sorted(memberships[group_id], key=lambda r: to_int(row_get(r, "LSE_ID"))):
            add_projlist(project_key(group), lease, group_qualifier(group))

    project_keys = sorted({row["PROJKEY"] for row in projlist})
    sort_columns = [
        ("RSV_CAT", "A", "Y"),
        ("CLASS", "A", "Y"),
        ("RSV_CLASS", "A", "Y"),
        ("STATE", "A", "Y"),
        ("FIELD", "A", "Y"),
        ("LEASE", "A", "N"),
        ("RSC_SORT", "A", "N"),
        ("LSE_ID", "A", "N"),
    ]
    sortfilters = [
        {
            "PROJKEY": projkey,
            "SEQNUM": index,
            "TABLEALIAS": "M",
            "TABLECOLUMN": column,
            "SORTORDER": order,
            "SORTBREAK": brk,
        }
        for projkey in project_keys
        for index, (column, order, brk) in enumerate(sort_columns)
    ]

    memberships_by_project = {DEFAULT_PROJECT_KEY: leases}
    for group in groups:
        group_id = to_int(row_get(group, "GRP_ID"))
        if group_id in memberships and not is_all_cases_group(group):
            memberships_by_project[project_key(group)] = memberships[group_id]

    selfilters: list[dict[str, Any]] = []
    for projkey, member_leases in sorted(memberships_by_project.items()):
        filters = [{
            "PROJKEY": projkey,
            "SEQNUM": 0,
            "TABLEALIAS": "M",
            "TABLECOLUMN": "TAI_EXCLUDE",
            "OPERATOR": "is Null",
            "OPERATORTEXT": "",
            "ANDOR": "And",
            "DATATYPE": 12,
        }]
        category_names = sorted({
            build_category_name(category_by_id.get(to_int(row_get(lease, "PDP_CATEGORY", "RSV_CATEGORY", default=0))), to_int(row_get(lease, "PDP_CATEGORY", "RSV_CATEGORY", default=0)))
            for lease in member_leases
        })
        if category_names:
            filters.append({
                "PROJKEY": projkey,
                "SEQNUM": len(filters),
                "TABLEALIAS": "M",
                "TABLECOLUMN": "RSV_CAT",
                "OPERATOR": "is one of",
                "OPERATORTEXT": ", ".join(category_names),
                "ANDOR": "And",
                "DATATYPE": 12,
            })
        if projkey != DEFAULT_PROJECT_KEY:
            lease_id_list = ", ".join(f"{to_int(row_get(lease, 'LSE_ID')):.2f}" for lease in sorted(member_leases, key=lambda r: to_int(row_get(r, "LSE_ID"))))
            filters.append({
                "PROJKEY": projkey,
                "SEQNUM": len(filters),
                "TABLEALIAS": "M",
                "TABLECOLUMN": "LSE_ID",
                "OPERATOR": "is one of",
                "OPERATORTEXT": lease_id_list,
                "ANDOR": "",
                "DATATYPE": 8,
            })
        filters[-1]["ANDOR"] = ""
        selfilters.extend(filters)

    scenarios: list[dict[str, Any]] = []
    seen_scenarios: set[tuple[str, int]] = set()

    def add_scenario(scen_name: str, data_sect: int, **values: Any) -> None:
        key = (scen_name, data_sect)
        if key in seen_scenarios:
            return
        row = {
            "DBSKEY": DEFAULT_DBSKEY, "SCEN_NAME": scen_name, "DATA_SECT": data_sect,
            "QUAL0": "", "QUAL1": "", "QUAL2": "", "QUAL3": "", "QUAL4": "",
            "QUAL5": "", "QUAL6": "", "QUAL7": "", "QUAL8": "", "QUAL9": "",
            "OWNER": "",
        }
        row.update(values)
        scenarios.append(row)
        seen_scenarios.add(key)

    for section in range(1, 10):
        add_scenario(DEFAULT_SCENARIO_NAME, section, QUAL0=DEFAULT_DATA_QUALIFIER, QUAL1=DEFAULT_REVIEW_QUALIFIER)

    for group in groups:
        qualifier = group_qualifier(group)
        for section in range(1, 7):
            add_scenario(qualifier, section)
        for section in (7, 8):
            add_scenario(qualifier, section, QUAL0=qualifier, QUAL1=DEFAULT_DATA_QUALIFIER)
        add_scenario(qualifier, 9)

    title = titles[0] if titles else {}
    asof = parse_date(row_get(title, "ASOF_DATE_DTTM", "ASOF_DATE", default="")) or date.today()
    maxecoyears = to_int(row_get(title, "MAXECOYEARS", default=50), default=50)
    adjusted_max = maxecoyears + asof.year - 2000
    if adjusted_max > 100:
        adjusted_max = 100
    dead_months = round(((asof - date(2000, 1, 1)).days) / (365.25 / 12), 0)
    remaining_months = 12 - asof.month + 1
    remaining_years = round(adjusted_max - (dead_months + remaining_months) / 12, 0)
    setupdata = [
        {"SECNAME": "TAURIS", "SECTYPE": "FRAME", "LINENUMBER": 1, "LINE": f"01/2000 {dead_months},{remaining_months},{remaining_years}*12"},
        {"SECNAME": "TAURIS", "SECTYPE": "FRAME", "LINENUMBER": 4, "LINE": asof.strftime("%m/%Y")},
        {"SECNAME": "TAURIS", "SECTYPE": "FRAME", "LINENUMBER": 2000, "LINE": f"1 -1 3 0 {adjusted_max}"},
    ]

    ac_setup = [{
        "SETUPNAME": "TAURIS", "DESCRIPTN": "Tauris conversion setup",
        "OWNER": "", "PBLIC": "Y",
        "FRAME": "TAURIS", "PW": "", "ESC": "", "CAPITAL": "",
        "CORPTAX": "", "SSROY": "", "SPECIAL": "", "VARATES": "",
        "DEFLINES": "", "COMLINES": "",
    }]

    if not daily:
        warnings.append("PHD_DAILY was not present; AC_TEST and AC_DAILY are empty.")
    economic_result = build_ac_economic_rows(economic_source_tables, selected_lease_ids)
    warnings.extend(economic_result.warnings)

    tables = {
        "AC_PROPERTY": ac_property,
        "AC_PRODUCT": ac_product,
        "AC_TEST": ac_test,
        "AC_DAILY": [],
        "AC_ECONOMIC": economic_result.rows,
        "ARLOOKUP": [],
        "AR_SIDEFILE": [],
        "AC_OWNER": ac_owner,
        "GROUPTEST": [],
        "AC_SCENARIO": scenarios,
        "AC_SETUP": ac_setup,
        "AC_SETUPDATA": setupdata,
        "PROJECT": project_rows,
        "PROJLIST": projlist,
        "SORTFILTERS": sortfilters,
        "SelFilters": selfilters,
    }
    return tables, warnings, {"acEconomic": economic_result.diagnostics}


def get_all_lease_ids(source_sqlite: Path) -> list[int]:
    with open_sqlite(source_sqlite) as conn:
        rows = conn.execute(
            'SELECT LSE_ID FROM "PHD_MAINLSE" ORDER BY CAST(LSE_ID AS INTEGER)'
        ).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


def export_aries_full_to_sqlite(source_sqlite: Path, aries_sqlite: Path, batch_size: int = 50) -> dict[str, Any]:
    all_ids = get_all_lease_ids(source_sqlite)
    all_warnings: list[str] = []
    table_counts: dict[str, int] = {}
    for batch_start in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[batch_start: batch_start + batch_size]
        tables, warnings, _ = build_aries_tables(source_sqlite, lease_ids=batch_ids)
        all_warnings.extend(warnings)
        write_aries_sqlite_tables(tables, aries_sqlite, append=batch_start > 0)
        for name, rows in tables.items():
            if name in PER_LEASE_TABLES:
                table_counts[name] = table_counts.get(name, 0) + len(rows)
            else:
                table_counts[name] = len(rows)
    return {
        "ariesSqlitePath": str(aries_sqlite),
        "totalLeases": len(all_ids),
        "tableCounts": table_counts,
        "warnings": all_warnings,
    }


def write_access_database_summary(tables: dict[str, list[dict[str, Any]]], template_path: Path, output_path: Path) -> Any:
    return write_access_database_with_defaults(
        tables,
        template_path,
        output_path,
        dbskey=DEFAULT_DBSKEY,
        date_parser=parse_date,
    )


def write_access_database(tables: dict[str, list[dict[str, Any]]], template_path: Path, output_path: Path) -> list[str]:
    summary = write_access_database_summary(tables, template_path, output_path)
    warnings = list(summary.warnings)
    for table in summary.tables.values():
        warnings.extend(table.warnings)
    return warnings


def export_aries(
    source_sqlite: Path,
    output_dir: Path,
    template_path: Path | None = None,
    accdb_path: Path | None = None,
    lease_ids: list[int] | None = None,
) -> AriesExportResult:
    source_sqlite = source_sqlite.resolve()
    output_dir = output_dir.resolve()
    csv_dir = output_dir / "csv"
    output_dir.mkdir(parents=True, exist_ok=True)

    tables, warnings, diagnostics = build_aries_tables(source_sqlite, lease_ids=lease_ids)
    write_csv_tables(tables, csv_dir)

    final_accdb_path: Path | None = None
    if accdb_path is not None:
        template_path = resolve_access_template_path(template_path)
        final_accdb_path = accdb_path.resolve()
        access_tables, access_economic = prepare_access_tables(tables)
        if access_economic["omittedReviewEconomicRows"]:
            warnings.append(access_economic["message"])
        access_summary = write_access_database_summary(access_tables, template_path.resolve(), final_accdb_path)
        warnings.extend(access_summary.warnings)
        for table in access_summary.tables.values():
            warnings.extend(table.warnings)
        diagnostics = diagnostics or {}
        diagnostics["accessEconomic"] = access_economic
        diagnostics["accessWriter"] = access_summary.to_dict()

    table_counts = {table: len(rows) for table, rows in tables.items()}
    result = AriesExportResult(
        source_sqlite=source_sqlite,
        output_dir=output_dir,
        csv_dir=csv_dir,
        accdb_path=final_accdb_path,
        table_counts=table_counts,
        warnings=warnings,
        diagnostics=diagnostics,
    )
    with (output_dir / "aries-export-summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Aries CSV/ACCDB review artifacts from a PHDWin SQLite export.")
    parser.add_argument("source_sqlite", help="SQLite database exported by the PHDWin-to-Aries MCP server")
    parser.add_argument("output", help="Output directory, Aries SQLite path, or Aries ACCDB path depending on flags")
    parser.add_argument("--output-sqlite", action="store_true", help="Write batched Aries tables to a SQLite database.")
    parser.add_argument("--batch-size", type=int, default=50, help="Lease batch size for --output-sqlite.")
    parser.add_argument(
        "--template",
        help="External Aries_Template.accdb path. If omitted, ARIES_TEMPLATE_ACCDB_PATH is used.",
    )
    parser.add_argument(
        "--accdb",
        nargs="?",
        const="__OUTPUT__",
        help="Optional output .accdb path. If no path is supplied, the output positional path is used.",
    )
    parser.add_argument("--lease-id", action="append", type=int, default=[], help="Optional lease id filter. Repeat for multiple leases.")
    args = parser.parse_args()
    output = Path(args.output)

    if args.output_sqlite or output.suffix.lower() in {".sqlite", ".db"}:
        result = export_aries_full_to_sqlite(
            Path(args.source_sqlite),
            output,
            batch_size=args.batch_size,
        )
        print(json.dumps(result, indent=2))
        return 0

    accdb_path: Path | None = None
    output_dir = output
    if args.accdb:
        accdb_path = output if args.accdb == "__OUTPUT__" else Path(args.accdb)
        output_dir = accdb_path.with_suffix("")

    result = export_aries(
        Path(args.source_sqlite),
        output_dir,
        template_path=Path(args.template) if args.template else None,
        accdb_path=accdb_path,
        lease_ids=args.lease_id or None,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
