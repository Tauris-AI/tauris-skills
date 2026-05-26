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
        for logical_table in args.tables:
            table_ref = resolve_table_reference(dataset_dir, logical_table)
            sql = f"SELECT * FROM {quote_identifier(table_ref)}"
            print(f"Testing {logical_table} -> {table_ref}")
            try:
                rows = cursor.execute(sql).fetchmany(args.limit)
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
