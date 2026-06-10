#!/usr/bin/env python3
"""Shared ARIES writer consumed by all source-specific resolvers.

Scope: single source of truth for ARIES table order, column aliases, schema
extensions, and serialisation to CSV, SQLite, and Access (.accdb).  Source-
specific resolvers (PHDWin, Enverus, Forecasting) build a
``dict[str, list[dict[str, Any]]]`` of resolved ARIES rows and hand them
here.  No PHD_*, Enverus, or forecasting-specific logic belongs in this file.

Key constants defined here:
    EXPORT_TABLE_ORDER  - canonical write order for all output formats
    GLOBAL_TABLES       - tables written once (not per-lease-batch)
    PER_LEASE_TABLES    - tables appended per batch during batched export
    ACCESS_COLUMN_ALIASES - maps template column names to source aliases
    ACCESS_SCHEMA_EXTENSIONS - columns added to the template at write time

Re-exports from ``aries_access_writer``:
    AriesAccessWriter, AriesAccessWriteSummary, AriesTableWriteSummary,
    AriesAccessWriterError, write_access_database
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


# ---------------------------------------------------------------------------
# Dynamic loader for the canonical AriesAccessWriter class.
# ---------------------------------------------------------------------------

def _locate_access_writer() -> Path:
    """Resolve the canonical aries_access_writer.py path relative to this file."""
    return Path(__file__).resolve().parent.parent / "mcp-servers" / "aries-mcp" / "aries_access_writer.py"


def _load_access_writer() -> ModuleType:
    writer_path = _locate_access_writer()
    if not writer_path.exists():
        raise ImportError(f"Shared Aries Access writer not found at {writer_path}")
    spec = importlib.util.spec_from_file_location("tauris_shared_aries_access_writer", writer_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load shared Aries Access writer from {writer_path}")
    cached = sys.modules.get(spec.name)
    if cached is not None:
        return cached
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_access_writer = _load_access_writer()

# Re-export canonical Access writer API.
AriesAccessWriter = _access_writer.AriesAccessWriter
AriesAccessWriteSummary = _access_writer.AriesAccessWriteSummary
AriesTableWriteSummary = _access_writer.AriesTableWriteSummary
AriesAccessWriterError = _access_writer.AriesAccessWriterError
write_access_database = _access_writer.write_access_database


# ---------------------------------------------------------------------------
# Constants — fixed ARIES table/column contracts.
# ---------------------------------------------------------------------------

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
    "AC_SETUP",
    "AC_SETUPDATA",
    "PROJECT",
    "PROJLIST",
    "SORTFILTERS",
    "SelFilters",
]

ACCESS_STALE_DATA_TABLES = [
    "AC_DETAIL",
    "AC_ECOSUM",
    "AC_FCST",
    "AC_MONTHLY",
    "AC_NOTE",
    "AC_ONELINE",
    "AC_PZFCST",
    "AC_RATIO",
    "AC_RESERVES",
    "AC_WELL",
    "GROUPLIST",
    "GROUPS",
]

ACCESS_SCHEMA_EXTENSIONS: dict[str, list[dict[str, str]]] = {
    "AC_PROPERTY": [
        {"name": "SRC_DB", "accdb_type": "VARCHAR(255)"},
    ],
}

ACCESS_COLUMN_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "AC_PROPERTY": {
        "SEQNUM": ("SEQ",),
        "FIRST_PROD": ("PROD_START",),
    },
    "AC_PRODUCT": {
        "DAYSON": ("DAYS_ON",),
    },
    "AC_TEST": {
        "T_DATE": ("DATE", "TEST_DATE"),
        "WTR_RATE": ("WATER_RATE",),
        "M_FWHP": ("TUBINGPRESSURE",),
        "C_SIWHP": ("CASINGPRESSURE", "SITP"),
    },
    "AC_DAILY": {
        "D_DATE": ("DATE",),
        "WATER": ("WATER_RATE",),
    },
}

PER_LEASE_TABLES = {
    "AC_PROPERTY",
    "AC_PRODUCT",
    "AC_TEST",
    "AC_DAILY",
    "AC_ECONOMIC",
    "AC_OWNER",
    "GROUPTEST",
    "PROJLIST",
}

GLOBAL_TABLES = {
    "PROJECT",
    "AC_SCENARIO",
    "AC_SETUP",
    "AC_SETUPDATA",
    "SORTFILTERS",
    "SelFilters",
    "ARLOOKUP",
    "AR_SIDEFILE",
}


# ---------------------------------------------------------------------------
# Shared utility helpers (source-agnostic).
# ---------------------------------------------------------------------------

def _clean_text(value: Any, max_len: int | None = None) -> str:
    text = "" if value is None else str(value).strip()
    text = " ".join(text.split())
    if max_len is not None:
        return text[:max_len]
    return text


def _row_get(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    by_upper = {str(k).upper(): v for k, v in row.items()}
    for name in names:
        if name.upper() in by_upper:
            value = by_upper[name.upper()]
            return default if value is None else value
    return default


# ---------------------------------------------------------------------------
# Review-row filtering — shared between CSV/SQLite (keep) and Access (omit).
# ---------------------------------------------------------------------------

DEFAULT_REVIEW_QUALIFIER = "PY_REVIEW"


def is_review_economic_row(row: dict[str, Any]) -> bool:
    qualifier = _clean_text(_row_get(row, "QUALIFIER", default="")).upper()
    keyword = _clean_text(_row_get(row, "KEYWORD", default="")).upper()
    return qualifier == DEFAULT_REVIEW_QUALIFIER or keyword.startswith("PY_REVIEW")


def prepare_access_tables(
    tables: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Prepare final Access payloads from review/export tables.

    Review-only ``PY_REVIEW`` economic rows are useful diagnostics in CSV and
    SQLite outputs, but they are not valid final Aries economic syntax.  Do not
    write them to ``AC_ECONOMIC`` in a generated ``.accdb``.
    """
    access_tables = {
        table_name: [dict(row) for row in rows]
        for table_name, rows in tables.items()
    }
    original_economic_rows = access_tables.get("AC_ECONOMIC", [])
    final_economic_rows = [
        row
        for row in original_economic_rows
        if not is_review_economic_row(row)
    ]
    omitted_review_rows = len(original_economic_rows) - len(final_economic_rows)
    access_tables["AC_ECONOMIC"] = final_economic_rows

    if omitted_review_rows:
        for scenario in access_tables.get("AC_SCENARIO", []):
            for key, value in list(scenario.items()):
                if str(key).upper().startswith("QUAL") and _clean_text(value).upper() == DEFAULT_REVIEW_QUALIFIER:
                    scenario[key] = ""

    if omitted_review_rows and not final_economic_rows:
        status = "empty"
    elif omitted_review_rows:
        status = "final_rows_present"
    elif final_economic_rows:
        status = "final_rows_present"
    else:
        status = "empty"

    return access_tables, {
        "omittedReviewEconomicRows": omitted_review_rows,
        "accessEconomicRowCount": len(final_economic_rows),
        "status": status,
        "complete": bool(final_economic_rows),
        "message": (
            "Review-only PY_REVIEW economic rows were omitted from the Access export."
            if omitted_review_rows
            else "No review-only economic rows were present in the Access payload."
        ),
    }


# ---------------------------------------------------------------------------
# CSV writer.
# ---------------------------------------------------------------------------

def write_csv_tables(
    tables: dict[str, list[dict[str, Any]]],
    csv_dir: Path,
    append: bool = False,
) -> None:
    csv_dir.mkdir(parents=True, exist_ok=True)
    for table_name in EXPORT_TABLE_ORDER:
        rows = tables.get(table_name, [])
        is_per_lease = table_name in PER_LEASE_TABLES
        path = csv_dir / f"{table_name}.csv"
        if append and is_per_lease and path.exists():
            with path.open("r", newline="", encoding="utf-8") as handle:
                columns = next(csv.reader(handle), [])
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                for row in rows:
                    writer.writerow({column: row.get(column, "") for column in columns})
            continue
        if not rows and append and not is_per_lease:
            continue
        columns = sorted({column for row in rows for column in row.keys()}, key=str.upper)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column, "") for column in columns})


# ---------------------------------------------------------------------------
# SQLite writer / reader.
# ---------------------------------------------------------------------------

def write_aries_sqlite_tables(
    tables: dict[str, list[dict[str, Any]]],
    aries_sqlite: Path,
    append: bool = False,
) -> None:
    aries_sqlite.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(aries_sqlite) as conn:
        for table_name in EXPORT_TABLE_ORDER:
            rows = tables.get(table_name, [])
            is_per_lease = table_name in PER_LEASE_TABLES
            if not rows:
                if not append or not is_per_lease:
                    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                continue
            columns = sorted({column for row in rows for column in row.keys()}, key=str.upper)
            if append and is_per_lease:
                col_defs = ", ".join(f'"{column}" TEXT' for column in columns)
                conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs})')
                existing = {
                    row[1]
                    for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                }
                for column in columns:
                    if column not in existing:
                        conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column}" TEXT')
            else:
                conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                col_defs = ", ".join(f'"{column}" TEXT' for column in columns)
                conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')
            col_list = ", ".join(f'"{column}"' for column in columns)
            placeholders = ", ".join("?" for _ in columns)
            conn.executemany(
                f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})',
                [[str(row.get(column, "") or "") for column in columns] for row in rows],
            )
        conn.commit()


def read_aries_sqlite_tables(aries_sqlite: Path) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    with sqlite3.connect(aries_sqlite) as conn:
        conn.row_factory = sqlite3.Row
        for table_name in EXPORT_TABLE_ORDER:
            try:
                rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
                tables[table_name] = [dict(row) for row in rows]
            except Exception:
                tables[table_name] = []
    return tables


# ---------------------------------------------------------------------------
# Access template resolution.
# ---------------------------------------------------------------------------

def resolve_access_template_path(template_path: Path | None = None) -> Path:
    if template_path is not None:
        return template_path
    env_path = os.environ.get("ARIES_TEMPLATE_ACCDB_PATH")
    if env_path:
        return Path(env_path)
    raise FileNotFoundError(
        "Aries Access export requires an external template .accdb. "
        "Pass --template, pass template_accdb_path to the MCP tool, or set ARIES_TEMPLATE_ACCDB_PATH. "
        "The Cowork plugin does not bundle Aries_Template.accdb because raw database templates can trip "
        "Cowork's compression-ratio guard."
    )


# ---------------------------------------------------------------------------
# Convenience wrappers for Access export with standard defaults.
# ---------------------------------------------------------------------------

def write_access_database_with_defaults(
    tables: dict[str, list[dict[str, Any]]],
    template_path: Path,
    output_path: Path,
    *,
    dbskey: str,
    date_parser: Any = None,
) -> Any:
    """Write resolved ARIES rows to an Access .accdb using standard defaults.

    Callers supply their own ``dbskey`` and optional ``date_parser``.
    Table order, stale-data tables, schema extensions, and column aliases are
    taken from the shared constants defined in this module.
    """
    return write_access_database(
        tables,
        template_path,
        output_path,
        dbskey=dbskey,
        table_order=EXPORT_TABLE_ORDER,
        stale_data_tables=ACCESS_STALE_DATA_TABLES,
        schema_extensions=ACCESS_SCHEMA_EXTENSIONS,
        column_aliases=ACCESS_COLUMN_ALIASES,
        date_parser=date_parser,
    )
