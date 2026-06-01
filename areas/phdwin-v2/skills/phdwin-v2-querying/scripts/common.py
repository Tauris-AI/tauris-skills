#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Iterable


def is_wsl() -> bool:
    return "microsoft" in platform.release().lower() or "wsl" in platform.version().lower()


def import_pyodbc():
    try:
        import pyodbc  # type: ignore

        return pyodbc
    except ImportError:
        return None


def list_odbc_drivers() -> list[str]:
    pyodbc = import_pyodbc()
    if pyodbc is None:
        return []
    return list(pyodbc.drivers())


def find_driver_name(drivers: Iterable[str]) -> str | None:
    for driver in drivers:
        lower = driver.lower()
        if "topspeed" in lower or "softvelocity" in lower or "clarion" in lower:
            return driver
    return None


def detect_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".phz":
        return "phz"
    if suffix == ".zip":
        return "zip"
    if suffix in {".phd", ".mod"}:
        return "native"
    if suffix in {".sqlite", ".db"}:
        return "sqlite"
    if path.is_dir():
        return "dataset-folder"
    return "unknown"


def find_dataset_files(dataset_dir: Path) -> tuple[Path | None, Path | None]:
    phd = None
    mod = None
    for child in sorted(dataset_dir.iterdir()):
        if child.is_file():
            suffix = child.suffix.lower()
            if suffix == ".phd" and phd is None:
                phd = child
            elif suffix == ".mod" and mod is None:
                mod = child
    return phd, mod


def build_topspeed_connection_string(dataset_dir: Path, driver_name: str) -> str:
    phd, mod = find_dataset_files(dataset_dir)
    parts = [
        f"Driver={{{driver_name}}}",
        f"DBQ={dataset_dir}",
        "Extension=*",
        "UlongAsDate=N",
        "NoDot=N",
        "NullEmptyStr=N",
        "Oem=Y",
    ]
    if phd is not None:
        parts.append(f"PhdFileName={phd.name}")
        parts.append(f"FullFileName={phd}")
    if mod is not None:
        parts.append(f"ModFileName={mod.name}")
    return ";".join(parts)


def validate_dataset_dir(dataset_dir: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    if not dataset_dir.exists():
        problems.append(f"Dataset folder does not exist: {dataset_dir}")
        return False, problems
    if not dataset_dir.is_dir():
        problems.append(f"Dataset path is not a folder: {dataset_dir}")
        return False, problems
    phd, _ = find_dataset_files(dataset_dir)
    if phd is None:
        problems.append("No .phd file found in dataset folder")
    return len(problems) == 0, problems


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def resolve_table_reference(dataset_dir: Path, logical_table: str) -> str:
    phd, mod = find_dataset_files(dataset_dir)
    normalized = logical_table.upper()

    if normalized.startswith("PHD_"):
        if phd is None:
            raise ValueError("Cannot resolve PHD table without a .phd file")
        return f"{phd.name}\\&{normalized[4:]}"
    if normalized.startswith("MOD_"):
        if mod is None:
            raise ValueError("Cannot resolve MOD table without a .mod file")
        return f"{mod.name}\\&{normalized[4:]}"
    if normalized.startswith("{{PHD}}") or normalized.startswith("{{MOD}}"):
        raise ValueError("Use logical table names like PHD_MAINLSE or MOD_SCEN, not placeholders")
    if mod is not None and normalized in {
        "SCEN",
        "MODPRODVAL",
        "MODSEGMENT",
        "TEMPLATE",
        "KEY",
        "CANPRICE",
        "CURRENCY",
        "TIMESTAMP",
        "VERSION",
    }:
        return f"{mod.name}\\&{normalized}"
    if phd is None:
        raise ValueError("Cannot resolve table without a .phd file")
    return f"{phd.name}\\&{normalized}"


def print_environment_summary() -> None:
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"WSL: {'yes' if is_wsl() else 'no'}")
    print(f"CWD: {os.getcwd()}")
