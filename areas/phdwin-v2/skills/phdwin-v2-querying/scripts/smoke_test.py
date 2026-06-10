#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    build_topspeed_connection_string,
    find_driver_name,
    import_pyodbc,
    list_odbc_drivers,
    quote_identifier,
    resolve_table_reference,
    validate_dataset_dir,
)


def cursor_table_names(cursor) -> list[str]:
    table_names: list[str] = []
    for row in cursor.tables(tableType="TABLE"):
        try:
            table_name = row.table_name
        except AttributeError:
            table_name = row[2]
        if table_name:
            table_names.append(str(table_name))
    return table_names


def logical_table_base(logical_table: str) -> str:
    normalized = logical_table.upper()
    if normalized.startswith("PHD_") or normalized.startswith("MOD_"):
        return normalized[4:]
    return normalized


def match_native_table(actual_tables: list[str], logical_table: str, resolved_table: str) -> str:
    base = logical_table_base(logical_table)
    upper = logical_table.upper()
    prefer_mod = upper.startswith("MOD_")

    for actual in actual_tables:
        sep = actual.find("\\&")
        bare = actual[sep + 2:] if sep != -1 else actual
        file_part = actual[:sep].upper() if sep != -1 else ""
        is_mod_file = file_part.endswith(".MOD")
        if bare.upper() == base.upper() and prefer_mod == is_mod_file:
            return actual

    for actual in actual_tables:
        sep = actual.find("\\&")
        bare = actual[sep + 2:] if sep != -1 else actual
        if bare.upper() == base.upper():
            return actual

    actual_by_upper = {table.upper(): table for table in actual_tables}
    for candidate in [resolved_table, base, logical_table]:
        match = actual_by_upper.get(candidate.upper())
        if match:
            return match

    for table in actual_tables:
        upper_table = table.upper()
        if upper_table.endswith(f"\\&{base}") or upper_table.endswith(f"&{base}") or upper_table.endswith(f".{base}"):
            return table
    return resolved_table


def fetch_sample(cursor, table_name: str, limit: int):
    identifiers = [
        quote_identifier(table_name, dialect="topspeed"),
        table_name,
    ]
    last_error: Exception | None = None
    for identifier in identifiers:
        try:
            return cursor.execute(f"SELECT * FROM {identifier}").fetchmany(limit)
        except Exception as exc:  # pragma: no cover - driver-specific
            last_error = exc
    raise last_error or RuntimeError(f"Unable to select from {table_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only smoke tests against a PhdWIN dataset folder.")
    parser.add_argument("dataset_dir", help="Folder containing .phd and optional .mod files")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["PHD_MAINLSE", "PHD_OWNER", "PHD_FORCAST", "PHD_MONHIST"],
        help="Logical tables to test, e.g. PHD_MAINLSE MOD_SCEN",
    )
    parser.add_argument("--limit", type=int, default=1, help="Rows to fetch from each table")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).resolve()
    valid, problems = validate_dataset_dir(dataset_dir)
    if not valid:
        for problem in problems:
            print(problem)
        return 1

    pyodbc = import_pyodbc()
    if pyodbc is None:
        print("pyodbc is not installed in this Python environment.")
        return 2

    driver_name = find_driver_name(list_odbc_drivers())
    if driver_name is None:
        print("Clarion/TopSpeed ODBC driver not found.")
        return 3

    conn_str = build_topspeed_connection_string(dataset_dir, driver_name)
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-specific
        print(f"Failed to open dataset through ODBC: {exc}")
        return 4

    try:
        cursor = conn.cursor()
        actual_tables = cursor_table_names(cursor)
        for logical_table in args.tables:
            table_ref = resolve_table_reference(dataset_dir, logical_table)
            native_table = match_native_table(actual_tables, logical_table, table_ref)
            print(f"Testing {logical_table} -> {native_table}")
            try:
                rows = fetch_sample(cursor, native_table, args.limit)
                print(f"  OK, fetched {len(rows)} row(s)")
            except Exception as exc:  # pragma: no cover - environment-specific
                print(f"  FAILED: {exc}")
                return 5
    finally:
        conn.close()

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
