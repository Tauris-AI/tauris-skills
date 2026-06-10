#!/usr/bin/env python3
"""Forecasting area E2E test: Enverus production CSV → profile → ARIES tables → CSV/SQLite.

Restarts from scratch each run (removes all outputs first).
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

AREA_DIR = Path(__file__).resolve().parent
REPO_ROOT = AREA_DIR.parents[1]
OUTPUT_DIR = AREA_DIR / "output"

sys.path.insert(0, str(REPO_ROOT / "areas" / "forecasting" / "mcp-servers" / "forecasting-mcp"))
sys.path.insert(0, str(REPO_ROOT / "areas" / "aries" / "lib"))


PRODUCTION_ZIP = AREA_DIR / "env_csv-Production-badec_2026-06-04.zip"
WELLS_ZIP = AREA_DIR / "env_csv-Wells-e8117_2026-06-04.zip"

ENVERUS_COLUMN_MAP = {
    "WellName": "WellName",
    "ProducingMonth": "Date",
    "LiquidsProd_BBL": "Oil",
    "GasProd_MCF": "Gas",
    "WaterProd_BBL": "Water",
}


def clean_outputs() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Cleaned {OUTPUT_DIR}")


def extract_and_normalize_csv(limit_wells: int | None = None) -> Path:
    """Extract production zip and normalize columns for the forecasting MCP."""
    if not PRODUCTION_ZIP.exists():
        raise FileNotFoundError(f"Production zip not found: {PRODUCTION_ZIP}")

    with zipfile.ZipFile(PRODUCTION_ZIP) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            rows = list(reader)

    # Collect wells and optionally limit
    wells_seen: dict[str, bool] = {}
    for row in rows:
        well = (row.get("WellName") or "").strip()
        if well:
            wells_seen[well] = True

    selected_wells = set(sorted(wells_seen.keys())[:limit_wells]) if limit_wells else set(wells_seen.keys())
    print(f"  Source: {len(rows)} rows, {len(wells_seen)} wells → selected {len(selected_wells)}")

    # Write normalized CSV
    normalized_path = OUTPUT_DIR / "normalized_production.csv"
    out_fields = list(ENVERUS_COLUMN_MAP.values())
    with normalized_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=out_fields)
        writer.writeheader()
        for row in rows:
            well = (row.get("WellName") or "").strip()
            if well not in selected_wells:
                continue
            out_row = {}
            for src, dst in ENVERUS_COLUMN_MAP.items():
                out_row[dst] = row.get(src, "")
            writer.writerow(out_row)

    return normalized_path


def run_profile_and_recommend(csv_path: Path) -> dict[str, Any]:
    from forecasting_mcp import profile_and_recommend
    result = profile_and_recommend(str(csv_path))
    summary_path = OUTPUT_DIR / "profile_and_recommend.json"
    summary_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"  profile_and_recommend: {result['wellCount']} wells profiled")
    return result


def run_build_aries_tables(csv_path: Path) -> dict[str, list[dict[str, Any]]]:
    from forecasting_mcp import build_history_only_aries_tables
    tables = build_history_only_aries_tables(str(csv_path))
    print(f"  build_history_only_aries_tables: {len(tables['AC_PROPERTY'])} properties, {len(tables['AC_PRODUCT'])} products")
    return tables


def write_outputs(tables: dict[str, list[dict[str, Any]]]) -> None:
    from aries_writer import write_csv_tables, write_aries_sqlite_tables

    csv_dir = OUTPUT_DIR / "aries-csv"
    sqlite_path = OUTPUT_DIR / "forecasting_aries.sqlite"
    write_csv_tables(tables, csv_dir)
    write_aries_sqlite_tables(tables, sqlite_path)
    print(f"  Wrote CSV to {csv_dir}")
    print(f"  Wrote SQLite to {sqlite_path}")


def validate(tables: dict[str, list[dict[str, Any]]], profile_result: dict[str, Any]) -> dict[str, Any]:
    from aries_writer import EXPORT_TABLE_ORDER, read_aries_sqlite_tables

    errors: list[str] = []

    # Row count checks
    if len(tables["AC_PROPERTY"]) == 0:
        errors.append("AC_PROPERTY is empty")
    if len(tables["AC_PRODUCT"]) == 0:
        errors.append("AC_PRODUCT is empty")
    if tables["AC_ECONOMIC"] != []:
        errors.append("AC_ECONOMIC should be empty for history-only")

    # PROPNUM referential integrity
    propnums = {row["PROPNUM"] for row in tables["AC_PROPERTY"]}
    for row in tables["AC_PRODUCT"]:
        if row["PROPNUM"] not in propnums:
            errors.append(f"Orphan PROPNUM '{row['PROPNUM']}' in AC_PRODUCT")
            break

    # PROJLIST integrity
    import re
    for row in tables.get("PROJLIST", []):
        match = re.search(r"PROPNUM\s*=\s*'([^']+)'", row.get("PROPKEY", ""))
        if match and match.group(1) not in propnums:
            errors.append(f"Orphan PROJLIST PROPKEY: {row['PROPKEY']}")
            break

    # Profile result checks
    if profile_result["wellCount"] != len(tables["AC_PROPERTY"]):
        errors.append(
            f"Well count mismatch: profile={profile_result['wellCount']}, "
            f"properties={len(tables['AC_PROPERTY'])}"
        )

    # SQLite roundtrip
    sqlite_path = OUTPUT_DIR / "forecasting_aries.sqlite"
    if sqlite_path.exists():
        roundtrip = read_aries_sqlite_tables(sqlite_path)
        for table_name in EXPORT_TABLE_ORDER:
            orig = len(tables.get(table_name, []))
            rt = len(roundtrip.get(table_name, []))
            if orig != rt:
                errors.append(f"{table_name} SQLite roundtrip mismatch: orig={orig}, restored={rt}")

    # CSV roundtrip
    csv_dir = OUTPUT_DIR / "aries-csv"
    for table_name in EXPORT_TABLE_ORDER:
        csv_path = csv_dir / f"{table_name}.csv"
        if not csv_path.exists():
            errors.append(f"Missing CSV: {table_name}")
            continue
        with csv_path.open("r", newline="", encoding="utf-8") as handle:
            csv_rows = list(csv.DictReader(handle))
        orig = len(tables.get(table_name, []))
        if len(csv_rows) != orig:
            errors.append(f"{table_name} CSV row mismatch: orig={orig}, csv={len(csv_rows)}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "propertyCount": len(tables["AC_PROPERTY"]),
        "productCount": len(tables["AC_PRODUCT"]),
        "profiledWellCount": profile_result["wellCount"],
        "errors": errors,
    }
    return result


def main() -> int:
    print("=== Forecasting E2E Test ===")

    print("[1/5] Cleaning outputs...")
    clean_outputs()

    print("[2/5] Extracting and normalizing Enverus CSV...")
    csv_path = extract_and_normalize_csv(limit_wells=10)

    print("[3/5] Running profile_and_recommend...")
    profile_result = run_profile_and_recommend(csv_path)

    print("[4/5] Building ARIES tables and writing outputs...")
    tables = run_build_aries_tables(csv_path)
    write_outputs(tables)

    print("[5/5] Validating...")
    result = validate(tables, profile_result)

    summary_path = OUTPUT_DIR / "e2e_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if result["status"] == "PASS":
        print(f"  PASS: {result['propertyCount']} properties, {result['productCount']} products, 0 errors")
    else:
        print(f"  FAIL: {result['errors']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
