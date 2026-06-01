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
    validate_dataset_dir,
)

try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "fastmcp is not installed. Install prerequisites with: "
        "python -m pip install fastmcp pyodbc"
    ) from exc


mcp = FastMCP("phdwinv2")

DEFAULT_EXPORT_TABLES = [
    "MAINLSE",
    "TITLES",
    "OWNER",
    "GROUPS",
    "FORCAST",
    "MONHIST",
    "FILTER",
    "FILTERLINE",
    "SORT",
    "CLASS",
    "CATEGORY",
    "IDCODES",
    "IDLABELS",
]

SELECT_RE = re.compile(r"^\s*(?:/\*.*?\*/\s*)*(?:--[^\n]*\n\s*)*select\b", re.IGNORECASE | re.DOTALL)


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _rows_to_dicts(cursor: Any, rows: list[Any]) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description or []]
    return [
        {columns[index]: _json_value(value) for index, value in enumerate(row)}
        for row in rows
    ]


def _cursor_table_names(cursor: Any) -> list[str]:
    names: list[str] = []
    for row in cursor.tables(tableType="TABLE"):
        try:
            table_name = row.table_name
        except AttributeError:
            table_name = row[2]
        if table_name:
            names.append(str(table_name))
    return names


def _base_name(name: str) -> str:
    upper = name.upper()
    if upper.startswith("PHD_") or upper.startswith("MOD_"):
        return upper[4:]
    if "\\&" in upper:
        return upper.rsplit("\\&", 1)[1]
    if "&" in upper:
        return upper.rsplit("&", 1)[1]
    if "." in upper:
        return upper.rsplit(".", 1)[1]
    return upper


def _match_table(actual_tables: list[str], requested_table: str) -> str:
    requested_upper = requested_table.upper()
    requested_base = _base_name(requested_table)
    by_upper = {table.upper(): table for table in actual_tables}

    direct = by_upper.get(requested_upper)
    if direct:
        return direct

    for table in actual_tables:
        if _base_name(table) == requested_base:
            return table

    raise ValueError(f"Table not found: {requested_table}. Available examples: {actual_tables[:10]}")


def _require_select(sql: str) -> None:
    if not SELECT_RE.match(sql):
        raise ValueError("Only read-only SELECT queries are allowed.")
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise ValueError("Only one SELECT statement is allowed.")
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
    padded = f" {stripped.lower()} "
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
            "Clarion/TopSpeed ODBC driver not found. If it is not installed, get the "
            "SoftVelocity driver from https://softvelocity.myshopify.com/."
        )

    return pyodbc.connect(build_topspeed_connection_string(dataset_dir, driver_name), autocommit=True)


def _sqlite_tables(sqlite_path: Path) -> list[str]:
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


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
    """Inspect a .phz/.zip archive, extracted PHDWin folder, or SQLite database."""
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
        result.update({"tableCount": len(tables), "tables": summaries})
        return result

    dataset_dir = source if source.is_dir() else source.parent
    valid, problems = validate_dataset_dir(dataset_dir)
    phd, mod = find_dataset_files(dataset_dir) if dataset_dir.exists() else (None, None)
    result.update(
        {
            "datasetDir": str(dataset_dir),
            "validDataset": valid,
            "problems": problems,
            "phdFile": str(phd) if phd else None,
            "modFile": str(mod) if mod else None,
        }
    )
    return result


@mcp.tool
def extract_phz(phz_path: str, output_dir: str | None = None) -> dict[str, Any]:
    """Extract a PHDWin .phz/.zip package to a dataset folder."""
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
    return {"extractedTo": str(target), "phdFile": str(phd) if phd else None, "modFile": str(mod) if mod else None}


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
def list_tables(source_path: str) -> dict[str, Any]:
    """List tables from a native PHDWin dataset folder or SQLite database."""
    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        return {"source": str(source), "sourceType": "sqlite", "tables": _sqlite_tables(source)}

    dataset_dir = source if source.is_dir() else source.parent
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        tables = _cursor_table_names(cursor)
    return {"source": str(dataset_dir), "sourceType": "native", "tables": tables}


@mcp.tool
def get_columns(source_path: str, table_name: str) -> dict[str, Any]:
    """Get columns for a native PHDWin table or SQLite table."""
    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        with sqlite3.connect(source) as conn:
            columns = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        return {
            "source": str(source),
            "sourceType": "sqlite",
            "table": table_name,
            "columns": [{"name": column[1], "type": column[2], "notNull": bool(column[3])} for column in columns],
        }

    dataset_dir = source if source.is_dir() else source.parent
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        actual = _cursor_table_names(cursor)
        native_table = _match_table(actual, table_name)
        columns = [
            {"name": row.column_name, "type": row.type_name, "size": row.column_size, "nullable": row.nullable}
            for row in cursor.columns(table=native_table)
        ]
    return {"source": str(dataset_dir), "sourceType": "native", "table": native_table, "columns": columns}


@mcp.tool
def sample_table(source_path: str, table_name: str, limit: int = 10) -> dict[str, Any]:
    """Fetch sample rows from a native PHDWin table or SQLite table."""
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        with sqlite3.connect(source) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (limit,)).fetchall()
        return {"source": str(source), "sourceType": "sqlite", "table": table_name, "rows": [dict(row) for row in rows]}

    dataset_dir = source if source.is_dir() else source.parent
    with _open_topspeed(dataset_dir) as conn:
        cursor = conn.cursor()
        native_table = _match_table(_cursor_table_names(cursor), table_name)
        rows = cursor.execute(f"SELECT * FROM {quote_identifier(native_table, dialect='topspeed')}").fetchmany(limit)
        records = _rows_to_dicts(cursor, rows)
    return {"source": str(dataset_dir), "sourceType": "native", "table": native_table, "rows": records}


@mcp.tool
def run_select_query(source_path: str, sql: str, limit: int = 100) -> dict[str, Any]:
    """Run a read-only SELECT query against SQLite or a native PHDWin dataset."""
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    _require_select(sql)

    source = _path(source_path)
    source_type = detect_source_type(source)
    if source_type == "sqlite":
        with sqlite3.connect(source) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT * FROM ({sql.rstrip().rstrip(';')}) LIMIT ?", (limit,)).fetchall()
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
    """Export selected PHDWin native tables to SQLite."""
    source_dir = _path(dataset_dir)
    target = _path(sqlite_path)
    requested_tables = tables or DEFAULT_EXPORT_TABLES
    if target.exists() and not overwrite:
        raise FileExistsError(f"SQLite file already exists. Pass overwrite=true to replace: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    exported: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with _open_topspeed(source_dir) as source, sqlite3.connect(target) as dest:
        source_cursor = source.cursor()
        dest_cursor = dest.cursor()
        actual_tables = _cursor_table_names(source_cursor)
        for requested in requested_tables:
            try:
                native_table = _match_table(actual_tables, requested)
                rows = source_cursor.execute(f"SELECT * FROM {quote_identifier(native_table, dialect='topspeed')}").fetchall()
                column_names = [column[0] for column in source_cursor.description]
            except Exception as exc:
                skipped.append({"table": requested, "reason": str(exc)})
                continue

            sqlite_name = _base_name(requested)
            dest_cursor.execute(f'DROP TABLE IF EXISTS "{sqlite_name}"')
            create_cols = ", ".join(f'"{name}" TEXT' for name in column_names)
            dest_cursor.execute(f'CREATE TABLE "{sqlite_name}" ({create_cols})')
            if rows:
                placeholders = ", ".join("?" for _ in column_names)
                dest_cursor.executemany(
                    f'INSERT INTO "{sqlite_name}" VALUES ({placeholders})',
                    [[None if value is None else str(value) for value in row] for row in rows],
                )
            exported.append({"requestedTable": requested, "nativeTable": native_table, "sqliteTable": sqlite_name, "rowCount": len(rows)})
        dest.commit()
    return {"sqlitePath": str(target), "exported": exported, "skipped": skipped}


@mcp.tool
def diagnose_odbc(dataset_dir: str) -> dict[str, Any]:
    """Diagnose native PHDWin ODBC table names and selectable SQL forms."""
    source_dir = _path(dataset_dir)
    driver_name = os.environ.get("PHDWIN_ODBC_DRIVER") or find_driver_name(common_list_odbc_drivers())
    conn_str = build_topspeed_connection_string(source_dir, driver_name or "")
    results: list[dict[str, Any]] = []
    with _open_topspeed(source_dir) as conn:
        cursor = conn.cursor()
        tables = _cursor_table_names(cursor)
        test_table = tables[0] if tables else "MAINLSE"
        forms = [quote_identifier(test_table, dialect="topspeed"), test_table]
        for form in forms:
            try:
                rows = cursor.execute(f"SELECT * FROM {form}").fetchmany(1)
                results.append({"form": form, "status": "ok", "rowCount": len(rows)})
            except Exception as exc:
                results.append({"form": form, "status": "error", "error": str(exc)})
    return {"datasetDir": str(source_dir), "connectionString": conn_str, "actualTables": tables[:25], "testTable": test_table, "sqlForms": results}


@mcp.resource("phdwinv2://guide")
def guide() -> str:
    """Short guide for this PHDWin v2 MCP server."""
    return json.dumps(
        {
            "purpose": "Read-only local PHDWin v2 inspection, extraction, SQLite export, and SQLite/native query support.",
            "driverBoundary": {
                "requiresDriver": ".phz / .phd + .mod -> SQLite export",
                "noDriverRequired": "SQLite database -> review and query",
            },
            "driverUrl": "https://softvelocity.myshopify.com/",
            "defaultTables": DEFAULT_EXPORT_TABLES,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
