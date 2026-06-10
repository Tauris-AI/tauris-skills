#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from common import (
    build_topspeed_connection_string,
    detect_source_type,
    find_dataset_files,
    find_driver_name,
    import_pyodbc,
    is_wsl,
    list_odbc_drivers as common_list_odbc_drivers,
    quote_identifier,
    resolve_table_reference,
    validate_dataset_dir,
)
from export_sqlite import sqlite_table_name
from aries_export import (
    read_aries_sqlite_tables,
    resolve_access_template_path,
    write_access_database_summary,
    write_csv_tables,
)
from csv_export import export_sqlite_tables_to_csv

try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - depends on client machine setup
    raise SystemExit(
        "fastmcp is not installed. Install prerequisites with: "
        "python -m pip install fastmcp pyodbc"
    ) from exc


mcp = FastMCP("phdwin-v2")

DEFAULT_TABLES = [
    # PHD tables
    "PHD_TITLES", "PHD_MAINLSE", "PHD_PRODUCTNAMES", "PHD_OWNER", "PHD_GROUPS",
    "PHD_LIST", "PHD_ADJOWNER", "PHD_FILTER", "PHD_FILTERLINE", "PHD_SORT",
    "PHD_CLASS", "PHD_CATEGORY", "PHD_IDCODES", "PHD_IDLABELS", "PHD_FORCAST",
    "PHD_LSEPRODVAL", "PHD_LSESEGMENT", "PHD_MONHIST", "PHD_CUMVOL", "PHD_INVEST",
    "PHD_INVESTDESCR", "PHD_ECON", "PHD_ALLOCDAT", "PHD_ARCHIVE", "PHD_BASEUNITS",
    "PHD_COMMENT", "PHD_CONVENTIONS", "PHD_CONVENTIONUNITS", "PHD_CONVERSIONS",
    "PHD_DAILY", "PHD_ECOCHANGE", "PHD_ENERGYADJ", "PHD_FLUIDS", "PHD_FORCECHANGECAT",
    "PHD_GCA", "PHD_GCALINE", "PHD_GRAPHS", "PHD_GRAVITY", "PHD_LOGIN",
    "PHD_MSCINFO", "PHD_ORDER", "PHD_PHDCASECHANGE", "PHD_PHDWINEMAIL",
    "PHD_PHDWINUSER", "PHD_RISK", "PHD_ROYALTY", "PHD_ROYALTYADJ", "PHD_RPTGRP",
    "PHD_RPTLSE", "PHD_RPTSCRLN", "PHD_RPTSCRPT", "PHD_UNITS", "PHD_VERSION",
    "PHD_VOLUME", "PHD_ZONE",
    # MOD tables
    "MOD_CANPRICE", "MOD_CURRENCY", "MOD_CURRENCYRATE", "MOD_DEPRCHILD",
    "MOD_DEPRECIATION", "MOD_DEPRMODELS", "MOD_DEPRTYPE", "MOD_DEPRVALUES",
    "MOD_KEY", "MOD_MODID", "MOD_MODPRODVAL", "MOD_MODSEGMENT", "MOD_MODVER",
    "MOD_SCEN", "MOD_TEMPLATE", "MOD_TIMESTAMP", "MOD_TPLIDCODE",
    "MOD_TPLPRODSEGMENT", "MOD_TPLPRODUCT", "MOD_USER", "MOD_VERSION",
]
CONVERSION_REQUIRED_TABLES = [
    "PHD_TITLES",
    "PHD_MAINLSE",
    "PHD_OWNER",
    "PHD_GROUPS",
    "PHD_PRODUCTNAMES",
    "PHD_FORCAST",
    "PHD_MONHIST",
]
CONVERSION_RECOMMENDED_TABLES = [
    "PHD_ADJOWNER",
    "PHD_LIST",
    "PHD_FILTER",
    "PHD_FILTERLINE",
    "PHD_SORT",
    "PHD_CLASS",
    "PHD_CATEGORY",
    "PHD_IDCODES",
    "PHD_IDLABELS",
    "PHD_LSEPRODVAL",
    "PHD_LSESEGMENT",
    "PHD_CUMVOL",
    "PHD_INVEST",
    "PHD_INVESTDESCR",
    "PHD_ECON",
    "MOD_SCEN",
    "MOD_TEMPLATE",
]
SELECT_RE = re.compile(r"^\s*(?:/\*.*?\*/\s*)*(?:--[^\n]*\n\s*)*select\b", re.IGNORECASE | re.DOTALL)


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _rows_to_dicts(cursor: Any, rows: list[Any]) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description or []]
    return [
        {columns[index]: _json_value(value) for index, value in enumerate(row)}
        for row in rows
    ]


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _quote_sqlite_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _create_text_table(conn: sqlite3.Connection, table_name: str, columns: list[str]) -> None:
    column_sql = ", ".join(f"{_quote_sqlite_identifier(column)} TEXT" for column in columns)
    conn.execute(f"CREATE TABLE {_quote_sqlite_identifier(table_name)} ({column_sql})")


def _insert_dict_rows(
    conn: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    placeholders = ", ".join("?" for _ in columns)
    conn.executemany(
        f"INSERT INTO {_quote_sqlite_identifier(table_name)} VALUES ({placeholders})",
        [[row.get(column) for column in columns] for row in rows],
    )


def create_phdwin_review_template_sqlite(sqlite_path: Path, overwrite: bool = False) -> dict[str, Any]:
    """Create a synthetic PHDWin review fixture without shipping a binary SQLite file."""
    if sqlite_path.exists():
        if not overwrite:
            raise FileExistsError(f"SQLite template already exists: {sqlite_path}")
        sqlite_path.unlink()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    tables: dict[str, tuple[list[str], list[dict[str, Any]]]] = {
        "TEMPLATE_METADATA": (
            ["key", "value"],
            [
                {"key": "template_type", "value": "phdwin_review_sqlite"},
                {"key": "generated_by", "value": "phdwin_mcp_server.py"},
                {"key": "scope", "value": "Synthetic one-lease PHDWin review fixture with no client data"},
                {"key": "source_table_count", "value": str(len(DEFAULT_TABLES))},
            ],
        ),
        "PHD_TITLES": (
            ["PROJECT_ID", "PROJECT_NAME", "CASE_SET", "EFFECTIVE_DATE", "NOTES"],
            [{"PROJECT_ID": "TPL_PROJECT", "PROJECT_NAME": "SANITIZED TEMPLATE PROJECT", "CASE_SET": "BASE", "EFFECTIVE_DATE": "2026-01-01", "NOTES": "Synthetic template row for agent testing only"}],
        ),
        "PHD_MAINLSE": (
            ["LSE_ID", "LSE_NAME", "API", "OPERATOR", "FIELD", "COUNTY", "STATE", "RESERVE_CLASS", "RESERVE_CATEGORY", "GRP_ID", "FIRST_PROD_DATE"],
            [{"LSE_ID": "TPL_LSE_0001", "LSE_NAME": "SANITIZED LEASE 0001", "API": "00-000-00000", "OPERATOR": "REDACTED OPERATOR", "FIELD": "REDACTED FIELD", "COUNTY": "REDACTED COUNTY", "STATE": "XX", "RESERVE_CLASS": "PDP", "RESERVE_CATEGORY": "PROVED", "GRP_ID": "TPL_GRP_01", "FIRST_PROD_DATE": "2025-01-01"}],
        ),
        "PHD_PRODUCTNAMES": (
            ["PRODUCTCODE", "PRODUCT_NAME", "UNIT"],
            [
                {"PRODUCTCODE": "OIL", "PRODUCT_NAME": "Oil", "UNIT": "BBL"},
                {"PRODUCTCODE": "GAS", "PRODUCT_NAME": "Gas", "UNIT": "MCF"},
                {"PRODUCTCODE": "NGL", "PRODUCT_NAME": "NGL", "UNIT": "BBL"},
            ],
        ),
        "PHD_OWNER": (
            ["LSE_ID", "GRP_ID", "SEQ", "OWNER_NAME", "WORKING_INTEREST", "NET_REVENUE_INTEREST", "BURDEN"],
            [{"LSE_ID": "TPL_LSE_0001", "GRP_ID": "TPL_GRP_01", "SEQ": "1", "OWNER_NAME": "REDACTED OWNER", "WORKING_INTEREST": "1.000000", "NET_REVENUE_INTEREST": "0.800000", "BURDEN": "0.200000"}],
        ),
        "PHD_GROUPS": (
            ["GRP_ID", "GROUP_NAME", "DESCRIPTION"],
            [{"GRP_ID": "TPL_GRP_01", "GROUP_NAME": "SANITIZED GROUP", "DESCRIPTION": "Synthetic ownership/project group"}],
        ),
        "PHD_FORCAST": (
            ["LSE_ID", "ARCSEQ", "PRODUCTCODE", "START_DATE", "QI", "DI", "B_FACTOR", "MIN_DECLINE", "ECON_LIMIT"],
            [
                {"LSE_ID": "TPL_LSE_0001", "ARCSEQ": "1", "PRODUCTCODE": "OIL", "START_DATE": "2026-01-01", "QI": "100.0", "DI": "0.6500", "B_FACTOR": "0.9000", "MIN_DECLINE": "0.0600", "ECON_LIMIT": "1.0"},
                {"LSE_ID": "TPL_LSE_0001", "ARCSEQ": "1", "PRODUCTCODE": "GAS", "START_DATE": "2026-01-01", "QI": "600.0", "DI": "0.6200", "B_FACTOR": "0.8500", "MIN_DECLINE": "0.0600", "ECON_LIMIT": "10.0"},
            ],
        ),
        "PHD_MONHIST": (
            ["LSE_ID", "TYPE", "YEAR", "MONTH", "PRODUCTCODE", "VOLUME", "DAYS_ON"],
            [
                {"LSE_ID": "TPL_LSE_0001", "TYPE": "M", "YEAR": "2025", "MONTH": "1", "PRODUCTCODE": "OIL", "VOLUME": "3000.0", "DAYS_ON": "31"},
                {"LSE_ID": "TPL_LSE_0001", "TYPE": "M", "YEAR": "2025", "MONTH": "1", "PRODUCTCODE": "GAS", "VOLUME": "18000.0", "DAYS_ON": "31"},
            ],
        ),
        "PHD_CUMVOL": (
            ["LSE_ID", "PRODUCTCODE", "CUM_VOLUME", "AS_OF_DATE"],
            [
                {"LSE_ID": "TPL_LSE_0001", "PRODUCTCODE": "OIL", "CUM_VOLUME": "3000.0", "AS_OF_DATE": "2025-01-31"},
                {"LSE_ID": "TPL_LSE_0001", "PRODUCTCODE": "GAS", "CUM_VOLUME": "18000.0", "AS_OF_DATE": "2025-01-31"},
            ],
        ),
        "PHD_ECON": (
            ["LSE_ID", "EFFECTIVE_DATE", "LOE_FIXED", "LOE_VARIABLE", "SEV_TAX_RATE", "AD_VAL_TAX_RATE"],
            [{"LSE_ID": "TPL_LSE_0001", "EFFECTIVE_DATE": "2026-01-01", "LOE_FIXED": "2500.00", "LOE_VARIABLE": "1.25", "SEV_TAX_RATE": "0.0460", "AD_VAL_TAX_RATE": "0.0150"}],
        ),
        "PHD_INVEST": (
            ["LSE_ID", "INVEST_ID", "INVEST_DATE", "AMOUNT", "CATEGORY"],
            [{"LSE_ID": "TPL_LSE_0001", "INVEST_ID": "TPL_CAPEX_01", "INVEST_DATE": "2026-01-01", "AMOUNT": "100000.00", "CATEGORY": "FUTURE_CAPITAL"}],
        ),
        "PHD_INVESTDESCR": (
            ["INVEST_ID", "DESCRIPTION"],
            [{"INVEST_ID": "TPL_CAPEX_01", "DESCRIPTION": "Synthetic future capital"}],
        ),
        "MOD_SCEN": (
            ["SCEN_ID", "SCENARIO_NAME", "PRICE_SET", "COST_SET"],
            [{"SCEN_ID": "TPL_SCEN_01", "SCENARIO_NAME": "SANITIZED BASE CASE", "PRICE_SET": "TPL_PRICE", "COST_SET": "TPL_COST"}],
        ),
        "MOD_TEMPLATE": (
            ["TEMPLATE_ID", "TEMPLATE_NAME", "DESCRIPTION"],
            [{"TEMPLATE_ID": "TPL_MODEL_01", "TEMPLATE_NAME": "SANITIZED MODEL TEMPLATE", "DESCRIPTION": "Synthetic model assumptions"}],
        ),
    }
    placeholder_columns = ["LSE_ID", "GRP_ID", "SEQ", "SOURCE_ROLE", "SANITIZED_VALUE", "NOTES"]
    for table_name in DEFAULT_TABLES:
        tables.setdefault(
            table_name,
            (
                placeholder_columns,
                [{"LSE_ID": "TPL_LSE_0001", "GRP_ID": "TPL_GRP_01", "SEQ": "1", "SOURCE_ROLE": "placeholder_schema", "SANITIZED_VALUE": "SYNTHETIC", "NOTES": "Replace with real exported columns when a native PHDWin dataset is available"}],
            ),
        )

    conn = sqlite3.connect(sqlite_path)
    try:
        for table_name, (columns, rows) in tables.items():
            _create_text_table(conn, table_name, columns)
            _insert_dict_rows(conn, table_name, columns, rows)
        conn.commit()
    finally:
        conn.close()
    return {"sqlitePath": str(sqlite_path), "tableCount": len(tables), "sourceTableCount": len(DEFAULT_TABLES)}


def _cursor_table_names(cursor: Any) -> list[str]:
    table_names: list[str] = []
    for row in cursor.tables(tableType="TABLE"):
        try:
            table_name = row.table_name
        except AttributeError:
            table_name = row[2]
        if table_name:
            table_names.append(str(table_name))
    return table_names


def _logical_table_base(logical_table: str) -> str:
    normalized = logical_table.upper()
    if normalized.startswith("PHD_") or normalized.startswith("MOD_"):
        return normalized[4:]
    return normalized


def _match_native_table(actual_tables: list[str], logical_table: str, resolved_table: str) -> str:
    """Match a logical table name to an actual ODBC table name.

    The TopSpeed driver returns names like ``NEW.Phd\\&MAINLSE`` or
    ``NEW.MOD\\&SCEN``.  We match by comparing the part after ``\\&``
    (case-insensitive) and, when the logical prefix is known, preferring
    the file whose extension aligns (PHD_ → .Phd/.PHD, MOD_ → .MOD).
    """
    base = _logical_table_base(logical_table)
    upper = logical_table.upper()
    prefer_mod = upper.startswith("MOD_")

    # Build a lookup: bare name (after \& or just the name) → actual table string
    for actual in actual_tables:
        sep = actual.find("\\&")
        bare = actual[sep + 2:] if sep != -1 else actual
        file_part = actual[:sep].upper() if sep != -1 else ""
        is_mod_file = file_part.endswith(".MOD")
        if bare.upper() == base.upper():
            if prefer_mod == is_mod_file:
                return actual  # exact file-type match
    # Fallback: any file with matching bare name
    for actual in actual_tables:
        sep = actual.find("\\&")
        bare = actual[sep + 2:] if sep != -1 else actual
        if bare.upper() == base.upper():
            return actual

    # Last resort: original candidates
    candidates = [resolved_table, base, logical_table]
    actual_by_upper = {table.upper(): table for table in actual_tables}
    for candidate in candidates:
        match = actual_by_upper.get(candidate.upper())
        if match:
            return match

    suffixes = [f"\\&{base}", f"&{base}", f".{base}"]
    for table in actual_tables:
        upper = table.upper()
        if any(upper.endswith(suffix) for suffix in suffixes):
            return table

    return resolved_table


def _execute_select_all(cursor: Any, table_name: str) -> list[Any]:
    """Select all rows using the exact table name returned by ODBC metadata.

    Double-quote form must come first — the TopSpeed driver returns names like
    ``NEW.Phd\\&MAINLSE`` which only work when double-quoted.
    """
    identifiers = [
        '"' + table_name.replace('"', '""') + '"',
        quote_identifier(table_name, dialect="topspeed"),
        table_name,
    ]
    last_error: Exception | None = None
    for identifier in identifiers:
        try:
            return cursor.execute(f"SELECT * FROM {identifier}").fetchall()
        except Exception as exc:  # pragma: no cover - driver-specific
            last_error = exc
    raise last_error or RuntimeError(f"Unable to select from {table_name}")


def _require_select(sql: str) -> None:
    if not SELECT_RE.match(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise ValueError("Only one SELECT statement is allowed.")
    lower = stripped.lower()
    blocked = [
        " insert ",
        " update ",
        " delete ",
        " drop ",
        " alter ",
        " create ",
        " truncate ",
        " attach ",
        " detach ",
        " pragma ",
        " vacuum ",
        " replace ",
    ]
    padded = f" {lower} "
    for token in blocked:
        if token in padded:
            raise ValueError(f"Blocked non-read-only SQL token: {token.strip()}")


def _open_topspeed(dataset_dir: Path):
    valid, problems = validate_dataset_dir(dataset_dir)
    if not valid:
        raise ValueError("; ".join(problems))

    pyodbc = import_pyodbc()
    if pyodbc is None:
        raise RuntimeError("pyodbc is not installed in this Python environment.")

    driver_name = os.environ.get("PHDWIN_ODBC_DRIVER") or find_driver_name(common_list_odbc_drivers())
    if driver_name is None:
        raise RuntimeError(
            "Clarion/TopSpeed ODBC driver not found. If it is installed under a nonstandard "
            "name, set PHDWIN_ODBC_DRIVER in the Cowork MCP server env config. "
            "If it is not installed, get the SoftVelocity driver from "
            "https://softvelocity.myshopify.com/."
        )

    conn_str = build_topspeed_connection_string(dataset_dir, driver_name)
    return pyodbc.connect(conn_str, autocommit=True)


def _sqlite_tables(sqlite_path: Path) -> list[str]:
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


def _sqlite_count(sqlite_path: Path, table_name: str) -> int | None:
    if table_name not in _sqlite_tables(sqlite_path):
        return None
    with sqlite3.connect(sqlite_path) as conn:
        return int(conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0])


def _native_count(dataset_dir: Path, logical_table: str) -> int | None:
    try:
        table_ref = resolve_table_reference(dataset_dir, logical_table)
        conn = _open_topspeed(dataset_dir)
    except Exception:
        return None
    try:
        cursor = conn.cursor()
        actual_tables = _cursor_table_names(cursor)
        native_table = _match_native_table(actual_tables, logical_table, table_ref)
        table_identifier = quote_identifier(native_table, dialect="topspeed")
        row = cursor.execute(f"SELECT COUNT(*) FROM {table_identifier}").fetchone()
        return int(row[0]) if row is not None else None
    except Exception:
        return None
    finally:
        conn.close()


def _count_logical_table(source: Path, logical_table: str) -> int | None:
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        return _sqlite_count(source, logical_table.upper())
    dataset_dir = source if source.is_dir() else source.parent
    return _native_count(dataset_dir, logical_table)


@mcp.tool
def env_check() -> dict[str, Any]:
    """Check local Python, pyodbc, and Clarion/TopSpeed ODBC driver availability."""
    pyodbc = import_pyodbc()
    drivers = common_list_odbc_drivers()
    matched = find_driver_name(drivers)
    env_driver = os.environ.get("PHDWIN_ODBC_DRIVER")
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cwd": os.getcwd(),
        "wsl": is_wsl(),
        "pyodbcInstalled": pyodbc is not None,
        "pyodbcVersion": getattr(pyodbc, "version", None) if pyodbc is not None else None,
        "odbcDrivers": drivers,
        "driverOverrideEnv": env_driver,
        "clarionTopSpeedDriver": matched,
        "readyForNativePhdwin": pyodbc is not None and (matched is not None or env_driver is not None),
        "driverDownloadUrl": "https://softvelocity.myshopify.com/" if matched is None and env_driver is None else None,
    }


@mcp.tool
def inspect_source(source_path: str, sqlite_table_limit: int = 25) -> dict[str, Any]:
    """Inspect a .phz/.zip archive, extracted PhdWIN dataset folder, or SQLite export."""
    source = _path(source_path)
    source_type = detect_source_type(source)
    result: dict[str, Any] = {
        "source": str(source),
        "exists": source.exists(),
        "sourceType": source_type,
    }
    if not source.exists():
        return result

    if source_type in {"phz", "zip"}:
        with zipfile.ZipFile(source, "r") as archive:
            names = archive.namelist()
        result.update(
            {
                "archiveEntryCount": len(names),
                "phdFiles": [name for name in names if name.lower().endswith(".phd")],
                "modFiles": [name for name in names if name.lower().endswith(".mod")],
                "nextStep": "extract_phz",
            }
        )
        return result

    if source_type == "sqlite":
        tables = _sqlite_tables(source)
        summaries = []
        with sqlite3.connect(source) as conn:
            for table in tables[:sqlite_table_limit]:
                count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                columns = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
                summaries.append(
                    {
                        "table": table,
                        "rowCount": count,
                        "columns": [column[1] for column in columns],
                    }
                )
        result.update({"tables": summaries, "tableCount": len(tables)})
        return result

    dataset_dir = source if source.is_dir() else source.parent
    valid, problems = validate_dataset_dir(dataset_dir)
    phd, mod = find_dataset_files(dataset_dir) if dataset_dir.exists() else (None, None)
    result.update(
        {
            "datasetDir": str(dataset_dir),
            "validDataset": valid,
            "problems": problems,
            "phdFile": phd.name if phd else None,
            "modFile": mod.name if mod else None,
            "note": "Use the dataset folder, not the .phd/.mod file, as the ODBC target.",
        }
    )
    return result


@mcp.tool
def extract_phz(phz_path: str, output_dir: str | None = None) -> dict[str, Any]:
    """Extract a PhdWIN .phz/.zip archive to a dataset folder."""
    source = _path(phz_path)
    if not source.exists():
        raise FileNotFoundError(f"Missing archive: {source}")
    if source.suffix.lower() not in {".phz", ".zip"}:
        raise ValueError(f"Expected a .phz or .zip file, got: {source.name}")

    target = _path(output_dir) if output_dir else source.with_suffix("")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as archive:
        archive.extractall(target)

    phd, mod = find_dataset_files(target)
    return {
        "extractedTo": str(target),
        "phdFile": phd.name if phd else None,
        "modFile": mod.name if mod else None,
        "validDataset": phd is not None,
    }


@mcp.tool
def list_odbc_drivers() -> dict[str, Any]:
    """List installed ODBC drivers and identify the likely Clarion/TopSpeed driver."""
    drivers = common_list_odbc_drivers()
    return {
        "drivers": drivers,
        "driverOverrideEnv": os.environ.get("PHDWIN_ODBC_DRIVER"),
        "clarionTopSpeedDriver": find_driver_name(drivers),
    }


@mcp.tool
def resolve_table_name(dataset_dir: str, logical_table: str) -> dict[str, Any]:
    """Resolve a logical conversion table such as PHD_MAINLSE to the native ODBC table name."""
    source_dir = _path(dataset_dir)
    resolved = resolve_table_reference(source_dir, logical_table)
    return {"datasetDir": str(source_dir), "logicalTable": logical_table, "resolvedTable": resolved}


@mcp.tool
def list_tables(source_path: str) -> dict[str, Any]:
    """List tables from an extracted SQLite database or native PhdWIN dataset folder."""
    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        return {"source": str(source), "sourceType": "sqlite", "tables": _sqlite_tables(source)}

    dataset_dir = source if source.is_dir() else source.parent
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        tables = []
        for row in cursor.tables(tableType="TABLE"):
            try:
                tname = row.table_name
                ttype = row.table_type
            except AttributeError:
                tname = row[2]
                ttype = row[3]
            tables.append({"tableName": str(tname), "tableType": str(ttype)})
    return {"source": str(dataset_dir), "sourceType": "native", "tables": tables}


@mcp.tool
def get_columns(source_path: str, table_name: str) -> dict[str, Any]:
    """Get columns for a SQLite table or native logical table such as PHD_MAINLSE."""
    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        with sqlite3.connect(source) as conn:
            columns = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        return {
            "source": str(source),
            "sourceType": "sqlite",
            "table": table_name,
            "columns": [
                {"name": column[1], "type": column[2], "notNull": bool(column[3])}
                for column in columns
            ],
        }

    dataset_dir = source if source.is_dir() else source.parent
    table_ref = resolve_table_reference(dataset_dir, table_name)
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        columns = [
            {
                "name": row.column_name,
                "type": row.type_name,
                "size": row.column_size,
                "nullable": row.nullable,
            }
            for row in cursor.columns(table=table_ref)
        ]
    return {
        "source": str(dataset_dir),
        "sourceType": "native",
        "logicalTable": table_name,
        "resolvedTable": table_ref,
        "columns": columns,
    }


@mcp.tool
def sample_table(source_path: str, table_name: str, limit: int = 10) -> dict[str, Any]:
    """Fetch sample rows from a SQLite table or native logical table."""
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")

    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        sql = f'SELECT * FROM "{table_name}" LIMIT ?'
        with sqlite3.connect(source) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (limit,)).fetchall()
        return {
            "source": str(source),
            "sourceType": "sqlite",
            "table": table_name,
            "rows": [dict(row) for row in rows],
        }

    dataset_dir = source if source.is_dir() else source.parent
    table_ref = resolve_table_reference(dataset_dir, table_name)
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        actual_tables = _cursor_table_names(cursor)
        native_table = _match_native_table(actual_tables, table_name, table_ref)
        rows = _execute_select_all(cursor, native_table)[:limit]
        records = _rows_to_dicts(cursor, rows)
    return {
        "source": str(dataset_dir),
        "sourceType": "native",
        "logicalTable": table_name,
        "resolvedTable": native_table,
        "rows": records,
    }


@mcp.tool
def conversion_readiness(source_path: str) -> dict[str, Any]:
    """Check whether a PHDWin source has the core tables needed for PHDWin-to-Aries review."""
    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type in {"phz", "zip"}:
        return {
            "source": str(source),
            "sourceType": source_type,
            "ready": False,
            "nextStep": "Run extract_phz first, then call conversion_readiness on the extracted folder.",
        }

    table_results = []
    for table in [*CONVERSION_REQUIRED_TABLES, *CONVERSION_RECOMMENDED_TABLES]:
        count = _count_logical_table(source, table)
        table_results.append(
            {
                "logicalTable": table,
                "required": table in CONVERSION_REQUIRED_TABLES,
                "present": count is not None,
                "rowCount": count,
            }
        )

    missing_required = [
        row["logicalTable"] for row in table_results if row["required"] and not row["present"]
    ]
    present_required = [
        row["logicalTable"] for row in table_results if row["required"] and row["present"]
    ]
    return {
        "source": str(source),
        "sourceType": source_type,
        "ready": not missing_required,
        "presentRequiredTables": present_required,
        "missingRequiredTables": missing_required,
        "tables": table_results,
        "nextReviewSteps": [
            "Sample PHD_MAINLSE for well/case identity and location fields.",
            "Sample PHD_OWNER and PHD_GROUPS for WI/NRI and partner grouping.",
            "Sample PHD_FORCAST, PHD_LSESEGMENT, and PHD_LSEPRODVAL for forecast conversion.",
            "Sample PHD_FILTER, PHD_FILTERLINE, and PHD_SORT for project membership and seller views.",
            "Export SQLite before deeper conversion QA so Claude can query a stable derived copy.",
        ],
    }


@mcp.tool
def conversion_profile(source_path: str, sample_limit: int = 5) -> dict[str, Any]:
    """Build a compact PHDWin-to-Aries review profile with counts and samples from key tables."""
    if sample_limit < 1 or sample_limit > 25:
        raise ValueError("sample_limit must be between 1 and 25")

    source = _path(source_path)
    readiness = conversion_readiness(str(source))
    sample_tables = [
        "PHD_TITLES",
        "PHD_MAINLSE",
        "PHD_PRODUCTNAMES",
        "PHD_OWNER",
        "PHD_GROUPS",
        "PHD_LIST",
        "PHD_FORCAST",
        "PHD_MONHIST",
        "PHD_FILTER",
        "PHD_FILTERLINE",
        "PHD_SORT",
        "PHD_INVEST",
        "PHD_ECON",
        "MOD_SCEN",
    ]
    samples: dict[str, Any] = {}
    for table in sample_tables:
        try:
            samples[table] = sample_table(str(source), table, sample_limit)["rows"]
        except Exception as exc:
            samples[table] = {"error": str(exc)}

    return {
        "readiness": readiness,
        "samples": samples,
        "ariesTargets": {
            "property": ["AC_PROPERTY", "PROJECT", "PROJLIST"],
            "production": ["AC_PRODUCT", "AC_DAILY", "AC_TEST"],
            "economics": ["AC_ECONOMIC", "AC_SCENARIO", "AC_SETUPDATA"],
            "ownership": ["AC_OWNER", "GROUPTEST"],
            "lookups": ["ARLOOKUP", "AR_SIDEFILE", "SelFilters", "SORTFILTERS"],
        },
    }


@mcp.tool
def diagnose_odbc(dataset_dir: str) -> dict[str, Any]:
    """Diagnostic: test every SQL identifier form the TopSpeed driver might accept.

    Connects to the dataset folder, enumerates real table names via cursor.tables(),
    then tries every plausible SELECT form and reports which succeed or fail.
    Also reports the exact connection string used (with driver name redacted for brevity).
    """
    source_dir = _path(dataset_dir)
    phd, mod = find_dataset_files(source_dir)
    driver_name = os.environ.get("PHDWIN_ODBC_DRIVER") or find_driver_name(common_list_odbc_drivers())
    conn_str = build_topspeed_connection_string(source_dir, driver_name or "")

    results: list[dict[str, Any]] = []
    with _open_topspeed(source_dir) as conn:
        cursor = conn.cursor()
        actual = _cursor_table_names(cursor)
        # Pick first real table for testing
        test_table = actual[0] if actual else "MAINLSE"
        forms = [
            f'"{test_table}"',
            test_table,
        ]
        for form in forms:
            sql = f"SELECT * FROM {form}"
            try:
                rows = cursor.execute(sql).fetchmany(1)
                results.append({"form": form, "status": "ok", "rowCount": len(rows)})
            except Exception as exc:
                results.append({"form": form, "status": "error", "error": str(exc)})

    return {
        "datasetDir": str(source_dir),
        "phdFile": str(phd) if phd else None,
        "connectionString": conn_str,
        "actualTables": actual[:10],
        "testTable": test_table,
        "sqlForms": results,
    }


@mcp.tool
def run_select_query(source_path: str, sql: str, limit: int = 100) -> dict[str, Any]:
    """Run a read-only SELECT query against SQLite or a native PhdWIN dataset."""
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    _require_select(sql)

    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        wrapped_sql = f"SELECT * FROM ({sql.rstrip().rstrip(';')}) LIMIT ?"
        with sqlite3.connect(source) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(wrapped_sql, (limit,)).fetchall()
        return {"source": str(source), "sourceType": "sqlite", "rows": [dict(row) for row in rows]}

    dataset_dir = source if source.is_dir() else source.parent
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        rows = cursor.execute(sql).fetchmany(limit)
        records = _rows_to_dicts(cursor, rows)
    return {"source": str(dataset_dir), "sourceType": "native", "rows": records}


@mcp.tool
def export_sqlite(
    dataset_dir: str,
    sqlite_path: str,
    tables: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export selected native PhdWIN tables to SQLite for repeatable read-only analysis."""
    source_dir = _path(dataset_dir)
    target = _path(sqlite_path)
    table_names = tables or DEFAULT_TABLES
    if target.exists() and not overwrite:
        raise FileExistsError(f"SQLite file already exists. Pass overwrite=true to replace: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    exported: list[dict[str, Any]] = []
    with _open_topspeed(source_dir) as source, sqlite3.connect(target) as dest:
        source_cursor = source.cursor()
        dest_cursor = dest.cursor()
        actual_tables = _cursor_table_names(source_cursor)
        skipped: list[dict[str, Any]] = []
        for logical_table in table_names:
            try:
                table_ref = resolve_table_reference(source_dir, logical_table)
                native_table = _match_native_table(actual_tables, logical_table, table_ref)
                rows = _execute_select_all(source_cursor, native_table)
            except Exception as exc:
                skipped.append({"logicalTable": logical_table, "reason": str(exc)})
                continue
            column_names = [column[0] for column in source_cursor.description]
            sqlite_name = sqlite_table_name(logical_table)
            dest_cursor.execute(f'DROP TABLE IF EXISTS "{sqlite_name}"')
            create_cols = ", ".join(f'"{name}" TEXT' for name in column_names)
            dest_cursor.execute(f'CREATE TABLE "{sqlite_name}" ({create_cols})')
            if rows:
                placeholders = ", ".join("?" for _ in column_names)
                dest_cursor.executemany(
                    f'INSERT INTO "{sqlite_name}" VALUES ({placeholders})',
                    [[None if value is None else str(value) for value in row] for row in rows],
                )
            exported.append(
                {
                    "logicalTable": logical_table,
                    "resolvedTable": native_table,
                    "sqliteTable": sqlite_name,
                    "rowCount": len(rows),
                }
            )
        dest.commit()

    return {"sqlitePath": str(target), "exported": exported, "skipped": skipped}


@mcp.tool
def convert_to_aries_sqlite(
    phdwin_sqlite_path: str,
    aries_sqlite_path: str,
    batch_size: int = 50,
) -> dict[str, Any]:
    """Convert PHDWin SQLite to Aries SQLite in a subprocess with batched leases."""
    import subprocess
    import sys

    source = _path(phdwin_sqlite_path)
    target = _path(aries_sqlite_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().parent / "aries_export.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            str(source),
            str(target),
            "--output-sqlite",
            "--batch-size",
            str(batch_size),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Aries conversion failed:\n{proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"ariesSqlitePath": str(target), "stdout": proc.stdout}


@mcp.tool
def export_aries_to_csv(
    aries_sqlite_path: str,
    output_dir: str,
) -> dict[str, Any]:
    """Read Aries SQLite and write one CSV per Aries table."""
    tables = read_aries_sqlite_tables(_path(aries_sqlite_path))
    target = _path(output_dir)
    write_csv_tables(tables, target, append=False)
    return {"csvDir": str(target), "tableCounts": {name: len(rows) for name, rows in tables.items()}}


@mcp.tool
def export_table_csvs(
    sqlite_path: str,
    output_dir: str,
    tables: list[str] | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Export raw SQLite tables to one named CSV file per table.

    Use this when users want the extracted PHDWin tables as ordinary files
    that Claude Code, Excel, Power BI, or any local script can review without
    needing the Clarion driver or Access ODBC.
    """
    return export_sqlite_tables_to_csv(
        _path(sqlite_path),
        _path(output_dir),
        tables=tables,
        overwrite=overwrite,
    )


@mcp.tool
def create_phdwin_review_template(
    output_sqlite_path: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a local synthetic PHDWin review SQLite fixture from code.

    The Cowork plugin intentionally does not bundle the old binary
    phdwin_review_template.sqlite because highly compressible database files
    can trip Cowork's plugin compression-ratio guard.
    """
    return create_phdwin_review_template_sqlite(_path(output_sqlite_path), overwrite=overwrite)


@mcp.tool
def export_aries_to_accdb(
    aries_sqlite_path: str,
    output_accdb_path: str,
    template_accdb_path: str | None = None,
) -> dict[str, Any]:
    """Read Aries SQLite and write an Aries .accdb. Requires Access ODBC."""
    accdb = _path(output_accdb_path)
    template = resolve_access_template_path(_path(template_accdb_path) if template_accdb_path else None)
    tables = read_aries_sqlite_tables(_path(aries_sqlite_path))
    summary = write_access_database_summary(tables, template, accdb)
    warnings = list(summary.warnings)
    for table in summary.tables.values():
        warnings.extend(table.warnings)
    return {
        "accdbPath": str(accdb),
        "tableCounts": {name: len(rows) for name, rows in tables.items()},
        "warnings": warnings,
        "accessWriter": summary.to_dict(),
    }


@mcp.resource("phdwin://aries-conversion-map")
def aries_conversion_map() -> str:
    """High-level PHDWin-to-Aries conversion map for Claude Cowork."""
    return json.dumps(
        {
            "purpose": "Guide read-only PHDWin v2 inspection for Aries conversion readiness and QA.",
            "phdwinSources": {
                "projectHeader": ["PHD_TITLES"],
                "casesAndProperties": ["PHD_MAINLSE"],
                "productNames": ["PHD_PRODUCTNAMES"],
                "ownership": ["PHD_OWNER", "PHD_GROUPS", "PHD_LIST", "PHD_ADJOWNER"],
                "filtersAndSorts": ["PHD_FILTER", "PHD_FILTERLINE", "PHD_SORT"],
                "forecast": ["PHD_FORCAST", "PHD_LSESEGMENT", "PHD_LSEPRODVAL"],
                "history": ["PHD_MONHIST", "PHD_CUMVOL"],
                "economics": ["PHD_ECON", "PHD_INVEST", "PHD_INVESTDESCR", "MOD_SCEN", "MOD_TEMPLATE"],
                "lookups": ["PHD_CLASS", "PHD_CATEGORY", "PHD_IDCODES", "PHD_IDLABELS"],
            },
            "ariesTargets": {
                "property": ["AC_PROPERTY", "PROJECT", "PROJLIST"],
                "production": ["AC_PRODUCT", "AC_DAILY", "AC_TEST"],
                "economics": ["AC_ECONOMIC", "AC_SCENARIO", "AC_SETUPDATA"],
                "ownership": ["AC_OWNER", "GROUPTEST"],
                "lookups": ["ARLOOKUP", "AR_SIDEFILE", "SelFilters", "SORTFILTERS"],
            },
            "recommendedCoworkFlow": [
                "env_check",
                "inspect_source",
                "extract_phz if source is a .phz",
                "conversion_readiness",
                "conversion_profile",
                "export_sqlite to create a stable derived review database",
                "export_table_csvs when users want one CSV per extracted PHDWin table",
                "convert_to_aries_sqlite for batched Aries conversion",
                "export_aries_to_csv for Aries-named review tables from Aries SQLite",
                "export_aries_to_accdb on Windows when pyodbc and the Access ODBC driver are installed",
                "use run_select_query against SQLite for deeper QA",
            ],
        },
        indent=2,
    )


@mcp.resource("phdwin://aries-review-guide")
def aries_review_guide() -> str:
    """Short guidance for safe PHDWin-to-Aries source review through this MCP server."""
    return json.dumps(
        {
            "sourceTypes": {
                "native": "Use an extracted dataset folder containing one .phd file and optional .mod file.",
                "sqlite": "Use a prior SQLite export for repeatable analysis without the Clarion driver.",
                "phz": "Extract .phz first, then query the extracted folder.",
            },
            "safety": [
                "Native PHDWin tools are read-only.",
                "run_select_query blocks non-SELECT SQL.",
                "Export writes only to a new SQLite file unless overwrite=true is passed.",
            ],
            "commonTables": DEFAULT_TABLES,
            "conversionRequiredTables": CONVERSION_REQUIRED_TABLES,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
