#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

from common import (
    detect_source_type,
    find_dataset_files,
    find_driver_name,
    import_pyodbc,
    is_wsl,
    list_odbc_drivers,
    print_environment_summary,
    validate_dataset_dir,
)


SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(script_name: str, *args: str) -> int:
    cmd = [sys.executable, str(SCRIPT_DIR / script_name), *args]
    print(f"> {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd)


def command_env(_: argparse.Namespace) -> int:
    print_environment_summary()
    pyodbc = import_pyodbc()
    if pyodbc is None:
        print("pyodbc: missing")
        print("Clarion/TopSpeed driver: cannot check because pyodbc is unavailable")
        if is_wsl():
            print("WSL detected: use Windows Python if the ODBC driver is installed only on Windows.")
        return 1

    drivers = list_odbc_drivers()
    matched = find_driver_name(drivers)
    print(f"pyodbc: {pyodbc.version}")
    print(f"Installed ODBC drivers: {len(drivers)}")
    for driver in drivers:
        marker = " (Clarion/TopSpeed candidate)" if driver == matched else ""
        print(f"- {driver}{marker}")

    if matched is None:
        print("Clarion/TopSpeed driver: not found")
        if is_wsl():
            print("WSL detected: Linux Python usually cannot use a Windows-only ODBC driver directly.")
        return 2

    print(f"Clarion/TopSpeed driver: found ({matched})")
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    source_type = detect_source_type(source)
    print(f"Source: {source}")
    print(f"Detected type: {source_type}")

    if source_type == "sqlite":
        return inspect_sqlite(source, args.limit)

    if source_type in {"phz", "zip"}:
        print("A .phz is a ZIP-style PhdWIN archive and must be extracted before ODBC access.")
        print(f"Next command: {Path(sys.argv[0]).name} extract {source}")
        return 0

    dataset_dir = source if source.is_dir() else source.parent
    valid, problems = validate_dataset_dir(dataset_dir)
    if not valid:
        for problem in problems:
            print(problem)
        return 1

    phd, mod = find_dataset_files(dataset_dir)
    print(f"Dataset folder: {dataset_dir}")
    print(f".phd: {phd.name if phd else 'missing'}")
    print(f".mod: {mod.name if mod else 'missing'}")
    print("Use this folder as the ODBC datasource target.")
    return 0


def inspect_sqlite(sqlite_path: Path, limit: int) -> int:
    if not sqlite_path.exists():
        print(f"SQLite file does not exist: {sqlite_path}")
        return 1

    try:
        conn = sqlite3.connect(sqlite_path)
    except sqlite3.Error as exc:
        print(f"Failed to open SQLite file: {exc}")
        return 1

    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()
        tables = [row[0] for row in rows]
        print(f"SQLite tables: {len(tables)}")
        for table in tables[:limit]:
            count = cursor.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            columns = cursor.execute(f'PRAGMA table_info("{table}")').fetchall()
            column_names = ", ".join(column[1] for column in columns[:8])
            suffix = " ..." if len(columns) > 8 else ""
            print(f"- {table}: {count} row(s); columns: {column_names}{suffix}")
        if len(tables) > limit:
            print(f"... {len(tables) - limit} more table(s)")
    except sqlite3.Error as exc:
        print(f"Failed to inspect SQLite file: {exc}")
        return 1
    finally:
        conn.close()

    return 0


def command_extract(args: argparse.Namespace) -> int:
    script_args = [args.phz_path]
    if args.out:
        script_args.extend(["--out", args.out])
    return run_script("extract_phz.py", *script_args)


def command_smoke(args: argparse.Namespace) -> int:
    script_args = [args.dataset_dir]
    if args.tables:
        script_args.append("--tables")
        script_args.extend(args.tables)
    if args.limit is not None:
        script_args.extend(["--limit", str(args.limit)])
    return run_script("smoke_test.py", *script_args)


def command_export(args: argparse.Namespace) -> int:
    script_args = [args.dataset_dir, args.sqlite_path]
    if args.tables:
        script_args.append("--tables")
        script_args.extend(args.tables)
    return run_script("export_sqlite.py", *script_args)


def command_wizard(args: argparse.Namespace) -> int:
    script_args: list[str] = []
    if args.source:
        script_args.extend(["--source", args.source])
    return run_script("phdwin_wizard.py", *script_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phdwin-cli",
        description="Local read-only PhdWIN v2 extraction, inspection, and SQLite export helper.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    env_parser = subparsers.add_parser("env", help="Check Python, pyodbc, and installed ODBC drivers")
    env_parser.set_defaults(func=command_env)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a .phz/.zip, dataset folder, or extracted SQLite file")
    inspect_parser.add_argument("source", help="Path to a .phz/.zip, .phd/.mod dataset folder, .sqlite, or .db file")
    inspect_parser.add_argument("--limit", type=int, default=25, help="Maximum SQLite tables to summarize")
    inspect_parser.set_defaults(func=command_inspect)

    extract_parser = subparsers.add_parser("extract", help="Extract a .phz/.zip package to a dataset folder")
    extract_parser.add_argument("phz_path", help="Path to the .phz or .zip file")
    extract_parser.add_argument("--out", help="Output folder. Defaults to a sibling folder named after the archive.")
    extract_parser.set_defaults(func=command_extract)

    smoke_parser = subparsers.add_parser("smoke", help="Run read-only ODBC smoke queries against core tables")
    smoke_parser.add_argument("dataset_dir", help="Folder containing .phd and optional .mod files")
    smoke_parser.add_argument("--tables", nargs="+", help="Logical tables to test, e.g. PHD_MAINLSE MOD_SCEN")
    smoke_parser.add_argument("--limit", type=int, help="Rows to fetch from each table")
    smoke_parser.set_defaults(func=command_smoke)

    export_parser = subparsers.add_parser("export-sqlite", help="Export selected PhdWIN tables to SQLite")
    export_parser.add_argument("dataset_dir", help="Folder containing .phd and optional .mod files")
    export_parser.add_argument("sqlite_path", help="Destination SQLite file path")
    export_parser.add_argument("--tables", nargs="+", help="Logical tables to export, e.g. PHD_MAINLSE MOD_SCEN")
    export_parser.set_defaults(func=command_export)

    wizard_parser = subparsers.add_parser("wizard", help="Run the interactive local workflow wizard")
    wizard_parser.add_argument("--source", help="Optional starting path (.phz, dataset folder, or SQLite file)")
    wizard_parser.set_defaults(func=command_wizard)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
