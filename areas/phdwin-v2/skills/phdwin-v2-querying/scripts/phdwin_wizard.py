#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
)


SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(script_name: str, *args: str) -> int:
    cmd = [sys.executable, str(SCRIPT_DIR / script_name), *args]
    print(f"\n> {' '.join(cmd)}")
    return subprocess.call(cmd)


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def wizard(source_path: Path | None) -> int:
    print("PhdWIN V2 Local Runner Wizard")
    print("----------------------------")
    print_environment_summary()
    print()

    pyodbc = import_pyodbc()
    drivers = list_odbc_drivers()
    matched_driver = find_driver_name(drivers)
    if pyodbc is None:
        print("pyodbc: missing")
    else:
        print(f"pyodbc: available")
    print(f"Clarion/TopSpeed driver: {matched_driver or 'not found'}")
    if is_wsl():
        print("WSL detected: do not assume Linux Python can use a Windows-only ODBC driver.")

    source_value = str(source_path) if source_path else prompt("Enter the source path (.phz, dataset folder, or .sqlite/.db)")
    path = Path(source_value).expanduser().resolve()
    source_type = detect_source_type(path)
    print(f"Detected source type: {source_type}")

    if source_type == "phz":
        out_dir = prompt("Extraction output folder", str(path.with_suffix("")))
        rc = run_script("extract_phz.py", str(path), "--out", out_dir)
        if rc != 0:
            return rc
        path = Path(out_dir).resolve()
        source_type = "dataset-folder"

    if source_type in {"native", "dataset-folder"}:
        dataset_dir = path if path.is_dir() else path.parent
        phd, mod = find_dataset_files(dataset_dir)
        print(f"Dataset folder: {dataset_dir}")
        print(f".phd: {phd.name if phd else 'missing'}")
        print(f".mod: {mod.name if mod else 'missing'}")

        if matched_driver is None:
            print("Cannot continue with native-source extraction until the Clarion/TopSpeed ODBC driver is installed.")
            return 2
        if pyodbc is None:
            print("Cannot continue with native-source extraction until pyodbc is installed.")
            return 3

        next_step = prompt("Choose next step: smoke / sqlite / quit", "smoke").lower()
        if next_step == "smoke":
            return run_script("smoke_test.py", str(dataset_dir))
        if next_step == "sqlite":
            sqlite_path = prompt("SQLite output path", str(dataset_dir / "phdwin_extract.sqlite"))
            return run_script("export_sqlite.py", str(dataset_dir), sqlite_path)
        return 0

    if source_type == "sqlite":
        print("SQLite source detected. No Clarion driver is required for query work.")
        print(f"SQLite file: {path}")
        print("Next step: inspect tables and generate read-only SELECT queries.")
        return 0

    print("Unknown source type. Provide a .phz, .phd/.mod dataset folder, or .sqlite/.db file.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive wizard for local PhdWIN extraction and query setup.")
    parser.add_argument("--source", help="Optional starting path (.phz, dataset folder, or SQLite file)")
    args = parser.parse_args()
    source_path = Path(args.source).resolve() if args.source else None
    return wizard(source_path)


if __name__ == "__main__":
    raise SystemExit(main())
