#!/usr/bin/env python3
"""ARIES area E2E test: read SampleAriesClassic.accdb and validate structure.

Restarts from scratch each run (removes all outputs first).
Uses access-parser (pure Python, no ODBC driver required).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

AREA_DIR = Path(__file__).resolve().parent
REPO_ROOT = AREA_DIR.parents[1]
OUTPUT_DIR = AREA_DIR / "output"
SAMPLE_ACCDB = AREA_DIR / "SampleAriesClassic.accdb"

sys.path.insert(0, str(REPO_ROOT / "areas" / "aries" / "lib"))

EXPECTED_CORE_TABLES = {
    "AC_PROPERTY", "AC_PRODUCT", "AC_ECONOMIC", "AC_SCENARIO",
    "AC_SETUPDATA", "PROJECT", "PROJLIST", "SORTFILTERS",
}


def clean_outputs() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Cleaned {OUTPUT_DIR}")


def read_accdb(accdb_path: Path) -> dict[str, Any]:
    """Read .accdb with access-parser and return table inventory."""
    try:
        from access_parser import AccessParser
    except ImportError:
        raise RuntimeError("access-parser is required. Install with: pip install access-parser")

    db = AccessParser(str(accdb_path))
    table_names = db.catalog
    inventory: dict[str, dict[str, Any]] = {}

    for table_name in sorted(table_names):
        try:
            parsed_table = db.parse_table(table_name)
            columns = list(parsed_table.columns) if hasattr(parsed_table, "columns") else []
            row_count = len(parsed_table) if hasattr(parsed_table, "__len__") else 0
            inventory[table_name] = {
                "columnCount": len(columns),
                "rowCount": row_count,
                "columns": columns[:20],
            }
        except Exception as exc:
            inventory[table_name] = {
                "columnCount": 0,
                "rowCount": 0,
                "error": str(exc),
            }

    return {
        "path": str(accdb_path),
        "tableCount": len(table_names),
        "tables": inventory,
    }


def validate_structure(inventory: dict[str, Any]) -> dict[str, Any]:
    """Validate the ARIES database has expected structure."""
    errors: list[str] = []
    warnings: list[str] = []

    tables = inventory.get("tables", {})
    table_names_upper = {name.upper() for name in tables}

    # Check expected core tables exist
    for expected in EXPECTED_CORE_TABLES:
        if expected.upper() not in table_names_upper:
            errors.append(f"Missing expected table: {expected}")

    # Check AC_PROPERTY has content
    ac_property = None
    for name, info in tables.items():
        if name.upper() == "AC_PROPERTY":
            ac_property = info
            break
    if ac_property:
        if ac_property.get("rowCount", 0) == 0:
            warnings.append("AC_PROPERTY has 0 rows")
        else:
            print(f"  AC_PROPERTY: {ac_property['rowCount']} rows, {ac_property['columnCount']} columns")

    # Check AC_ECONOMIC has content
    ac_economic = None
    for name, info in tables.items():
        if name.upper() == "AC_ECONOMIC":
            ac_economic = info
            break
    if ac_economic:
        print(f"  AC_ECONOMIC: {ac_economic['rowCount']} rows, {ac_economic['columnCount']} columns")

    # Non-empty table count
    non_empty = sum(1 for info in tables.values() if info.get("rowCount", 0) > 0)
    print(f"  Non-empty tables: {non_empty}/{len(tables)}")

    # Verify shared writer can import
    try:
        from aries_writer import EXPORT_TABLE_ORDER, ACCESS_STALE_DATA_TABLES
        print(f"  Shared writer imports OK ({len(EXPORT_TABLE_ORDER)} export tables)")
    except Exception as exc:
        errors.append(f"Shared writer import failed: {exc}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "tableCount": inventory["tableCount"],
        "nonEmptyTableCount": non_empty,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    print("=== ARIES E2E Test ===")

    if not SAMPLE_ACCDB.exists():
        print(f"  SKIP: {SAMPLE_ACCDB.name} not found")
        return 0

    print("[1/3] Cleaning outputs...")
    clean_outputs()

    print("[2/3] Reading .accdb with access-parser...")
    inventory = read_accdb(SAMPLE_ACCDB)
    inventory_path = OUTPUT_DIR / "accdb_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, default=str), encoding="utf-8")
    print(f"  Read {inventory['tableCount']} tables from {SAMPLE_ACCDB.name}")

    print("[3/3] Validating structure...")
    result = validate_structure(inventory)

    summary_path = OUTPUT_DIR / "e2e_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if result["status"] == "PASS":
        print(f"  PASS: {result['tableCount']} tables, {result['nonEmptyTableCount']} non-empty")
    else:
        print(f"  FAIL: {result['errors']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
