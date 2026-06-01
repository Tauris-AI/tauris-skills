#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
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


def sqlite_table_name(logical_table: str) -> str:
    return logical_table.upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export selected PhdWIN tables to SQLite.")
    parser.add_argument("dataset_dir", help="Folder containing .phd and optional .mod files")
    parser.add_argument("sqlite_path", help="Destination SQLite file path")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["PHD_MAINLSE", "PHD_OWNER", "PHD_GROUPS", "PHD_FORCAST", "PHD_MONHIST"],
        help="Logical tables to export, e.g. PHD_MAINLSE MOD_SCEN",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).resolve()
    sqlite_path = Path(args.sqlite_path).resolve()
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

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn_str = build_topspeed_connection_string(dataset_dir, driver_name)

    try:
        source = pyodbc.connect(conn_str, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-specific
        print(f"Failed to open dataset through ODBC: {exc}")
        return 4

    target = sqlite3.connect(sqlite_path)
    try:
        source_cursor = source.cursor()
        target_cursor = target.cursor()

        for logical_table in args.tables:
            table_ref = resolve_table_reference(dataset_dir, logical_table)
            sql = f"SELECT * FROM {quote_identifier(table_ref)}"
            print(f"Exporting {logical_table} -> {sqlite_table_name(logical_table)}")
            rows = source_cursor.execute(sql).fetchall()
            column_names = [column[0] for column in source_cursor.description]

            sqlite_name = sqlite_table_name(logical_table)
            target_cursor.execute(f'DROP TABLE IF EXISTS "{sqlite_name}"')
            create_cols = ", ".join(f'"{name}" TEXT' for name in column_names)
            target_cursor.execute(f'CREATE TABLE "{sqlite_name}" ({create_cols})')

            if rows:
                placeholders = ", ".join("?" for _ in column_names)
                insert_sql = f'INSERT INTO "{sqlite_name}" VALUES ({placeholders})'
                target_cursor.executemany(
                    insert_sql,
                    [[None if value is None else str(value) for value in row] for row in rows],
                )
                print(f"  inserted {len(rows)} row(s)")
            else:
                print("  inserted 0 row(s)")

        target.commit()
    finally:
        source.close()
        target.close()

    print(f"SQLite export complete: {sqlite_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
