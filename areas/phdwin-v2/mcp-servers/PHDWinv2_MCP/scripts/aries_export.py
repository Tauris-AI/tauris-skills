#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DBSKEY = "168888"
DEFAULT_PROJECT_KEY = "00_RSV_CAT"
EXPORT_TABLE_ORDER = [
    "AC_PROPERTY",
    "AC_PRODUCT",
    "AC_TEST",
    "AC_DAILY",
    "AC_ECONOMIC",
    "ARLOOKUP",
    "AR_SIDEFILE",
    "AC_OWNER",
    "GROUPTEST",
    "AC_SCENARIO",
    "AC_SETUPDATA",
    "PROJECT",
    "PROJLIST",
    "SORTFILTERS",
    "SelFilters",
]


@dataclass
class AriesExportResult:
    source_sqlite: Path
    output_dir: Path
    csv_dir: Path
    accdb_path: Path | None
    table_counts: dict[str, int]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceSqlite": str(self.source_sqlite),
            "outputDir": str(self.output_dir),
            "csvDir": str(self.csv_dir),
            "accdbPath": str(self.accdb_path) if self.accdb_path else None,
            "tableCounts": self.table_counts,
            "warnings": self.warnings,
        }


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


def build_aries_tables(source_sqlite: Path, lease_ids: list[int] | None = None) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
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
        monhist = read_table(conn, "PHD_MONHIST")
        daily = read_table(conn, "PHD_DAILY")

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
    leases_by_id = {to_int(row_get(lease, "LSE_ID")): lease for lease in leases}
    memberships = build_project_membership(leases, groups, list_rows, owners, selected_lease_ids)

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

        ac_property.append({
            "DBSKEY": DEFAULT_DBSKEY,
            "PROPNUM": propnum_for_lease(lease_id),
            "SEQ": lease_id,
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
            "PROD_START": aries_date(row_get(lease, "SOP_DTTM", "SOP_DATE", "SOP", default="")),
            "PROD_END": aries_date(row_get(lease, "EOP_DTTM", "EOP_DATE", "EOP", default="")),
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
            idx = month - 1
            ac_product.append({
                "PROPNUM": propnum_for_lease(lease_id),
                "P_DATE": month_end(year, month),
                "OIL": to_float(row_get(row, f"PROD2_{idx}", f"PROD2{idx}", f"PROD2_{month}", f"PROD2{month}", default=0)),
                "GAS": to_float(row_get(row, f"PROD1_{idx}", f"PROD1{idx}", f"PROD1_{month}", f"PROD1{month}", default=0)),
                "WATER": to_float(row_get(row, f"PROD3_{idx}", f"PROD3{idx}", f"PROD3_{month}", f"PROD3{month}", default=0)),
                "WELLCOUNT": to_float(row_get(row, f"PROD4_{idx}", f"PROD4{idx}", f"PROD4_{month}", f"PROD4{month}", default=0)),
                "DAYS_ON": to_float(row_get(row, f"PROD5_{idx}", f"PROD5{idx}", f"PROD5_{month}", f"PROD5{month}", default=0)),
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
    for group in groups:
        qualifier = group_qualifier(group)
        for section in range(1, 7):
            scenarios.append({"DBSKEY": DEFAULT_DBSKEY, "SCEN_NAME": qualifier, "DATA_SECT": section})
        for section in (7, 8):
            scenarios.append({"DBSKEY": DEFAULT_DBSKEY, "SCEN_NAME": qualifier, "DATA_SECT": section, "QUAL0": qualifier, "QUAL1": "TAURIS"})
        scenarios.append({"DBSKEY": DEFAULT_DBSKEY, "SCEN_NAME": qualifier, "DATA_SECT": 9})

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

    if not daily:
        warnings.append("PHD_DAILY was not present; AC_TEST and AC_DAILY are empty.")
    warnings.append("AC_ECONOMIC forecast/economic line generation is intentionally conservative in this Python port; use CSV/ACCDB outputs for review and extend before relying on final economics.")

    tables = {
        "AC_PROPERTY": ac_property,
        "AC_PRODUCT": ac_product,
        "AC_TEST": ac_test,
        "AC_DAILY": [],
        "AC_ECONOMIC": [],
        "ARLOOKUP": [],
        "AR_SIDEFILE": [],
        "AC_OWNER": [],
        "GROUPTEST": [],
        "AC_SCENARIO": scenarios,
        "AC_SETUPDATA": setupdata,
        "PROJECT": project_rows,
        "PROJLIST": projlist,
        "SORTFILTERS": sortfilters,
        "SelFilters": selfilters,
    }
    return tables, warnings


def write_csv_tables(tables: dict[str, list[dict[str, Any]]], csv_dir: Path) -> None:
    csv_dir.mkdir(parents=True, exist_ok=True)
    for table_name in EXPORT_TABLE_ORDER:
        rows = tables.get(table_name, [])
        columns = sorted({column for row in rows for column in row.keys()}, key=str.upper)
        path = csv_dir / f"{table_name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column, "") for column in columns})


def access_columns(cursor: Any, table_name: str) -> list[str]:
    columns = []
    for row in cursor.columns(table=table_name):
        try:
            columns.append(str(row.column_name))
        except AttributeError:
            columns.append(str(row[3]))
    return columns


def access_table_names(cursor: Any) -> set[str]:
    names = set()
    for row in cursor.tables(tableType="TABLE"):
        try:
            names.add(str(row.table_name).upper())
        except AttributeError:
            names.add(str(row[2]).upper())
    return names


def q(identifier: str) -> str:
    return "[" + identifier.replace("]", "]]") + "]"


def write_access_database(tables: dict[str, list[dict[str, Any]]], template_path: Path, output_path: Path) -> list[str]:
    warnings: list[str] = []
    try:
        import pyodbc  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pyodbc is required for .accdb export. CSV export does not require pyodbc.") from exc

    if not template_path.exists():
        raise FileNotFoundError(f"Missing Aries Access template: {template_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, output_path)

    conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};Dbq={output_path};Pooling=false"
    with pyodbc.connect(conn_str, autocommit=False) as conn:
        cursor = conn.cursor()
        available_tables = access_table_names(cursor)
        for table_name in EXPORT_TABLE_ORDER:
            if table_name.upper() not in available_tables:
                warnings.append(f"Access table {table_name} not found in template; skipped.")
                continue
            rows = tables.get(table_name, [])
            columns = access_columns(cursor, table_name)
            columns_by_upper = {column.upper(): column for column in columns}
            try:
                cursor.execute(f"DELETE FROM {q(table_name)}")
            except Exception as exc:
                warnings.append(f"Could not clear {table_name}: {exc}")
                continue
            if not rows:
                continue
            insert_columns = [
                columns_by_upper[column.upper()]
                for column in sorted({key for row in rows for key in row.keys()}, key=str.upper)
                if column.upper() in columns_by_upper
            ]
            if not insert_columns:
                warnings.append(f"No matching Access columns for {table_name}; rows skipped.")
                continue
            placeholders = ", ".join("?" for _ in insert_columns)
            sql = f"INSERT INTO {q(table_name)} ({', '.join(q(column) for column in insert_columns)}) VALUES ({placeholders})"
            values = [
                [row_get(row, column, default=None) for column in insert_columns]
                for row in rows
            ]
            cursor.fast_executemany = False
            cursor.executemany(sql, values)
        conn.commit()
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

    tables, warnings = build_aries_tables(source_sqlite, lease_ids=lease_ids)
    write_csv_tables(tables, csv_dir)

    final_accdb_path: Path | None = None
    if accdb_path is not None:
        if template_path is None:
            template_path = Path(__file__).resolve().parents[1] / "reference" / "templates" / "Aries_Template.accdb"
        final_accdb_path = accdb_path.resolve()
        warnings.extend(write_access_database(tables, template_path.resolve(), final_accdb_path))

    table_counts = {table: len(rows) for table, rows in tables.items()}
    result = AriesExportResult(
        source_sqlite=source_sqlite,
        output_dir=output_dir,
        csv_dir=csv_dir,
        accdb_path=final_accdb_path,
        table_counts=table_counts,
        warnings=warnings,
    )
    with (output_dir / "aries-export-summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Aries CSV/ACCDB review artifacts from a PHDWin SQLite export.")
    parser.add_argument("source_sqlite", help="SQLite database exported by the PHDWin-to-Aries MCP server")
    parser.add_argument("output_dir", help="Output directory for Aries CSV files and summary JSON")
    parser.add_argument("--template", help="Aries_Template.accdb path. Defaults to packaged template.")
    parser.add_argument("--accdb", help="Optional output .accdb path. Requires Windows ACE Access ODBC driver and pyodbc.")
    parser.add_argument("--lease-id", action="append", type=int, default=[], help="Optional lease id filter. Repeat for multiple leases.")
    args = parser.parse_args()

    result = export_aries(
        Path(args.source_sqlite),
        Path(args.output_dir),
        template_path=Path(args.template) if args.template else None,
        accdb_path=Path(args.accdb) if args.accdb else None,
        lease_ids=args.lease_id or None,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
