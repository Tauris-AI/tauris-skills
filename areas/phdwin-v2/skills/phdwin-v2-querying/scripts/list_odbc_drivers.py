#!/usr/bin/env python3
from __future__ import annotations

from common import find_driver_name, import_pyodbc, is_wsl, list_odbc_drivers, print_environment_summary


def main() -> int:
    print_environment_summary()
    pyodbc = import_pyodbc()
    if pyodbc is None:
        print("pyodbc: missing")
        print("Install pyodbc in the local Python environment before using the ODBC path.")
        return 1

    drivers = list_odbc_drivers()
    print(f"pyodbc: {pyodbc.version}")
    print(f"Installed ODBC drivers: {len(drivers)}")
    for driver in drivers:
        print(f"- {driver}")

    matched = find_driver_name(drivers)
    if matched is None:
        print("Clarion/TopSpeed driver: not found")
        if is_wsl():
            print("Note: WSL Python usually cannot use a Windows-only ODBC driver directly.")
        return 2

    print(f"Clarion/TopSpeed driver: found ({matched})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
