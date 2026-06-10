#!/usr/bin/env python3
"""PHDWin v2 area E2E test: .phz → review SQLite → ARIES build → CSV/SQLite/Access.

Restarts from scratch each run (removes all outputs first).

Full pipeline stages (each stage skips gracefully when dependencies are missing):
  1. Extract .phz archive (pure Python — always works)
  2. Export native .phd/.mod → review SQLite (requires pyodbc + TopSpeed ODBC driver)
  3. Build ARIES tables from review SQLite
  4. Write CSV + SQLite exports
  5. Write .accdb Access export (requires pyodbc + Access ODBC driver + template)

Data sources (tried in order):
  1. Extract Phdwinv2-db/Puckett Field.phz → ODBC export → review SQLite
  2. Phdwinv2-db/review/puckett_review.sqlite  — pre-built real Puckett Field data
  3. Synthetic review SQLite with 3 wells (fallback when no driver available)
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
import sys
import zipfile
from pathlib import Path
from typing import Any

AREA_DIR = Path(__file__).resolve().parent
REPO_ROOT = AREA_DIR.parents[1]
OUTPUT_DIR = AREA_DIR / "output"
SCRIPTS = REPO_ROOT / "areas" / "phdwin-v2" / "mcp-servers" / "PHDWinv2_MCP" / "scripts"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT / "areas" / "aries" / "lib"))

PUCKETT_PHZ = AREA_DIR / "Phdwinv2-db" / "Puckett Field.phz"
PUCKETT_REVIEW = AREA_DIR / "Phdwinv2-db" / "review" / "puckett_review.sqlite"

# Well-known locations for Aries_Template.accdb (checked in order).
# Drop a cleared template into any of these paths to enable .accdb export.
TEMPLATE_SEARCH_PATHS = [
    AREA_DIR.parent / "aries" / "Aries_Template.accdb",      # shared e2e-local/aries/
    REPO_ROOT / "areas" / "aries" / "Aries_Template.accdb",  # repo-level fallback
]


def clean_outputs() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Also clean legacy output locations
    for legacy in [
        AREA_DIR / "Phdwinv2-db" / "review" / "puckett_aries.sqlite",
        AREA_DIR / "Phdwinv2-db" / "review" / "puckett_e2e_summary.json",
        AREA_DIR / "Phdwinv2-db" / "aries-csv",
    ]:
        if legacy.is_dir():
            shutil.rmtree(legacy)
        elif legacy.is_file():
            legacy.unlink()
    print(f"  Cleaned {OUTPUT_DIR}")


# ---------------------------------------------------------------------------
# Stage 1: .phz extraction
# ---------------------------------------------------------------------------

def extract_phz(phz_path: Path, output_dir: Path) -> dict[str, Any]:
    """Extract .phz archive to a dataset folder. Pure Python, no ODBC needed."""
    target = output_dir / "Puckett Field"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(phz_path, "r") as archive:
        archive.extractall(target)
    phd_files = sorted(p.name for p in target.iterdir() if p.is_file() and p.suffix.lower() == ".phd")
    mod_files = sorted(p.name for p in target.iterdir() if p.is_file() and p.suffix.lower() == ".mod")
    return {
        "extractedTo": str(target),
        "phdFiles": phd_files,
        "modFiles": mod_files,
        "validDataset": bool(phd_files),
    }


# ---------------------------------------------------------------------------
# Stage 2: native .phd/.mod → review SQLite via ODBC
# ---------------------------------------------------------------------------

def try_odbc_export(dataset_dir: Path, sqlite_path: Path) -> dict[str, Any]:
    """Try to export native PHDWin files to review SQLite via ODBC.

    Returns status dict; sqlite_path is created only on success.
    """
    from common import import_pyodbc, find_driver_name, list_odbc_drivers

    pyodbc = import_pyodbc()
    if pyodbc is None:
        return {"status": "skipped", "reason": "pyodbc not installed"}

    drivers = list_odbc_drivers()
    driver = find_driver_name(drivers)
    if driver is None:
        return {"status": "skipped", "reason": "TopSpeed/Clarion ODBC driver not found", "drivers": drivers}

    # Driver available — attempt the export
    from phdwin_mcp_server import export_sqlite as mcp_export_sqlite
    try:
        result = mcp_export_sqlite(str(dataset_dir), str(sqlite_path), overwrite=True)
        return {"status": "ok", "driver": driver, "export": result}
    except Exception as exc:
        return {"status": "failed", "reason": str(exc), "driver": driver}


# ---------------------------------------------------------------------------
# Stage 3: synthetic fallback
# ---------------------------------------------------------------------------

def make_synthetic_source(sqlite_path: Path) -> None:
    """Create a synthetic PHDWin review SQLite with 3 wells (integer LSE_IDs)."""
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("CREATE TABLE PHD_MAINLSE (LSE_ID TEXT, LSE_NAME TEXT)")
        conn.execute("INSERT INTO PHD_MAINLSE VALUES (?, ?)", ("1", "Synth Oil Well Alpha"))
        conn.execute("INSERT INTO PHD_MAINLSE VALUES (?, ?)", ("2", "Synth Oil Well Beta"))
        conn.execute("INSERT INTO PHD_MAINLSE VALUES (?, ?)", ("3", "Synth Gas Well Gamma"))

        conn.execute("CREATE TABLE PHD_PRODUCTNAMES (PRODUCTCODE TEXT, DESCR TEXT)")
        conn.execute("INSERT INTO PHD_PRODUCTNAMES VALUES (?, ?)", ("1", "Gas"))
        conn.execute("INSERT INTO PHD_PRODUCTNAMES VALUES (?, ?)", ("2", "Oil"))
        conn.execute("INSERT INTO PHD_PRODUCTNAMES VALUES (?, ?)", ("3", "Water"))

        conn.execute("CREATE TABLE PHD_GROUPS (GRP_ID TEXT, GRP_DESC TEXT)")
        conn.execute("INSERT INTO PHD_GROUPS VALUES (?, ?)", ("1", "All Cases"))

        conn.execute(
            "CREATE TABLE PHD_OWNER (LSE_ID TEXT, GRP_ID TEXT, SEQ TEXT, RESOLVEDDATE TEXT, LSENRI TEXT, WRKINT TEXT, REVINT TEXT)"
        )
        conn.execute("INSERT INTO PHD_OWNER VALUES (?, ?, ?, ?, ?, ?, ?)", ("1", "1", "1", "0", "0.75", "1.0", "0.75"))
        conn.execute("INSERT INTO PHD_OWNER VALUES (?, ?, ?, ?, ?, ?, ?)", ("2", "1", "1", "0", "0.80", "1.0", "0.80"))
        conn.execute("INSERT INTO PHD_OWNER VALUES (?, ?, ?, ?, ?, ?, ?)", ("3", "1", "1", "0", "0.65", "1.0", "0.65"))

        conn.execute(
            'CREATE TABLE PHD_MONHIST (LSE_ID TEXT, TYPE TEXT, YEAR TEXT, "PROD1$1" TEXT, "PROD2$1" TEXT, "PROD3$1" TEXT, "PROD4$1" TEXT, "PROD5$1" TEXT)'
        )
        for lse_id, gas, oil, water in [("1", "500", "100", "30"), ("2", "300", "80", "20"), ("3", "2000", "5", "40")]:
            conn.execute('INSERT INTO PHD_MONHIST VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (lse_id, "0", "2024", gas, oil, water, "1", "31"))
            conn.execute('INSERT INTO PHD_MONHIST VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (lse_id, "0", "2025", gas, oil, water, "1", "28"))

        conn.execute("CREATE TABLE PHD_FORCAST (LSE_ID TEXT, ARCSEQ TEXT, PRODUCTCODE TEXT, QI TEXT, DI TEXT)")
        conn.execute("INSERT INTO PHD_FORCAST VALUES (?, ?, ?, ?, ?)", ("1", "1", "2", "100", "0.25"))
        conn.execute("INSERT INTO PHD_FORCAST VALUES (?, ?, ?, ?, ?)", ("2", "1", "2", "80", "0.20"))
        conn.execute("INSERT INTO PHD_FORCAST VALUES (?, ?, ?, ?, ?)", ("3", "1", "1", "2000", "0.15"))

        conn.execute("CREATE TABLE PHD_ECON (LSE_ID TEXT, SEQ TEXT, OPCOST TEXT)")
        conn.execute("INSERT INTO PHD_ECON VALUES (?, ?, ?)", ("1", "1", "15.00"))
        conn.execute("INSERT INTO PHD_ECON VALUES (?, ?, ?)", ("2", "1", "12.50"))
        conn.execute("INSERT INTO PHD_ECON VALUES (?, ?, ?)", ("3", "1", "8.00"))

        conn.execute("CREATE TABLE PHD_INVEST (LSE_ID TEXT, SEQ TEXT, AMOUNT TEXT, INVESTDESCR_ID TEXT)")
        conn.execute("INSERT INTO PHD_INVEST VALUES (?, ?, ?, ?)", ("1", "1", "500000", "1"))

        conn.execute("CREATE TABLE PHD_INVESTDESCR (INVESTDESCR_ID TEXT, DESCR TEXT)")
        conn.execute("INSERT INTO PHD_INVESTDESCR VALUES (?, ?)", ("1", "Drilling"))

        conn.execute("CREATE TABLE PHD_LSESEGMENT (LSE_ID TEXT, SEQ TEXT, QI TEXT)")
        conn.execute("INSERT INTO PHD_LSESEGMENT VALUES (?, ?, ?)", ("1", "1", "100"))

        conn.execute("CREATE TABLE PHD_LSEPRODVAL (LSE_ID TEXT, SEQ TEXT, PRICE TEXT)")
        conn.execute("INSERT INTO PHD_LSEPRODVAL VALUES (?, ?, ?)", ("1", "1", "75.00"))

        conn.execute("CREATE TABLE MOD_SCEN (LSE_ID TEXT, SEQ TEXT, NAME TEXT)")
        conn.execute("INSERT INTO MOD_SCEN VALUES (?, ?, ?)", ("1", "1", "Base"))

        conn.execute("CREATE TABLE MOD_TEMPLATE (LSE_ID TEXT, SEQ TEXT, NAME TEXT)")
        conn.execute("INSERT INTO MOD_TEMPLATE VALUES (?, ?, ?)", ("1", "1", "Standard"))

        conn.execute("CREATE TABLE PHD_CUMVOL (LSE_ID TEXT, SEQ TEXT, PRODUCTCODE TEXT, CUMOIL TEXT)")
        conn.execute("INSERT INTO PHD_CUMVOL VALUES (?, ?, ?, ?)", ("1", "1", "2", "50000"))

        conn.commit()
    print(f"  Created synthetic source: {sqlite_path}")


# ---------------------------------------------------------------------------
# Source resolution: .phz → ODBC → pre-built review → synthetic
# ---------------------------------------------------------------------------

def resolve_source() -> tuple[Path, dict[str, Any]]:
    """Find or create a usable review SQLite. Returns (path, metadata)."""
    metadata: dict[str, Any] = {"phzExtracted": False, "odbcExport": None, "sourceType": "unknown"}

    # Stage 1: Extract .phz if present
    if PUCKETT_PHZ.exists():
        print(f"  Found .phz: {PUCKETT_PHZ}")
        extract_result = extract_phz(PUCKETT_PHZ, OUTPUT_DIR)
        metadata["phzExtracted"] = True
        metadata["phzExtract"] = extract_result
        print(f"  Extracted to {extract_result['extractedTo']}: {len(extract_result['phdFiles'])} .phd, {len(extract_result['modFiles'])} .mod")

        # Stage 2: Try ODBC export from extracted native files
        if extract_result["validDataset"]:
            dataset_dir = Path(extract_result["extractedTo"])
            odbc_sqlite = OUTPUT_DIR / "puckett_review.sqlite"
            odbc_result = try_odbc_export(dataset_dir, odbc_sqlite)
            metadata["odbcExport"] = odbc_result
            if odbc_result["status"] == "ok":
                print(f"  ODBC export succeeded: {odbc_sqlite}")
                metadata["sourceType"] = "odbc_export"
                return odbc_sqlite, metadata
            else:
                print(f"  ODBC export {odbc_result['status']}: {odbc_result.get('reason', '')}")
    else:
        print(f"  No .phz found at {PUCKETT_PHZ}")

    # Stage 2b: Use pre-built review SQLite if available
    if PUCKETT_REVIEW.exists():
        print(f"  Using pre-built review: {PUCKETT_REVIEW}")
        metadata["sourceType"] = "pre_built_review"
        return PUCKETT_REVIEW, metadata

    # Stage 3: Synthetic fallback
    synthetic = OUTPUT_DIR / "synthetic_review.sqlite"
    print("  No real data available, creating synthetic fixture...")
    make_synthetic_source(synthetic)
    metadata["sourceType"] = "synthetic"
    return synthetic, metadata


# ---------------------------------------------------------------------------
# Template resolution: well-known paths → env var
# ---------------------------------------------------------------------------

def find_aries_template() -> Path | None:
    """Search well-known paths then ARIES_TEMPLATE_ACCDB_PATH for a template .accdb."""
    for candidate in TEMPLATE_SEARCH_PATHS:
        if candidate.exists():
            return candidate
    env_path = os.environ.get("ARIES_TEMPLATE_ACCDB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Pipeline: review SQLite → ARIES tables → CSV + SQLite + .accdb
# ---------------------------------------------------------------------------

def run_pipeline(source_sqlite: Path) -> dict[str, Any]:
    """Run the full PHDWin → ARIES conversion pipeline."""
    from aries_export import (
        build_aries_tables,
        export_aries_full_to_sqlite,
        write_access_database_summary,
    )
    from aries_writer import (
        EXPORT_TABLE_ORDER,
        prepare_access_tables,
        read_aries_sqlite_tables,
        write_aries_sqlite_tables,
        write_csv_tables,
    )

    # Build tables
    tables, warnings, diagnostics = build_aries_tables(source_sqlite)
    print(f"  build_aries_tables: {len(tables['AC_PROPERTY'])} properties, {len(tables['AC_ECONOMIC'])} economic rows")
    if warnings:
        safe_warnings = [w.encode("ascii", "replace").decode("ascii") for w in warnings[:3]]
        print(f"  Warnings: {safe_warnings}{'...' if len(warnings) > 3 else ''}")

    # Write CSV
    csv_dir = OUTPUT_DIR / "aries-csv"
    write_csv_tables(tables, csv_dir)
    print(f"  Wrote CSV to {csv_dir}")

    # Write SQLite
    aries_sqlite = OUTPUT_DIR / "aries.sqlite"
    write_aries_sqlite_tables(tables, aries_sqlite)
    print(f"  Wrote SQLite to {aries_sqlite}")

    # Batched export test
    batched_sqlite = OUTPUT_DIR / "aries_batched.sqlite"
    batch_result = export_aries_full_to_sqlite(source_sqlite, batched_sqlite, batch_size=2)
    print(f"  Batched export: {batch_result['totalLeases']} leases in batches of 2")

    # Stage 5: Try .accdb export
    accdb_result: dict[str, Any] = {"status": "skipped", "reason": "not attempted"}
    accdb_path = OUTPUT_DIR / "puckett_aries_export.accdb"
    template_path = find_aries_template()
    if template_path is None:
        searched = [str(p) for p in TEMPLATE_SEARCH_PATHS]
        accdb_result = {"status": "skipped", "reason": "no template found", "searchedPaths": searched}
        print(f"  .accdb export skipped: no Aries template found")
        print(f"    Drop Aries_Template.accdb into one of:")
        for p in TEMPLATE_SEARCH_PATHS:
            print(f"      {p}")
        print(f"    Or set ARIES_TEMPLATE_ACCDB_PATH env var")
    else:
        try:
            access_tables, access_economic = prepare_access_tables(tables)
            summary = write_access_database_summary(access_tables, template_path, accdb_path)
            accdb_warnings = list(summary.warnings)
            for table in summary.tables.values():
                accdb_warnings.extend(table.warnings)
            accdb_result = {
                "status": "ok",
                "accdbPath": str(accdb_path),
                "templatePath": str(template_path),
                "accessEconomic": access_economic,
                "accessWriter": summary.to_dict(),
                "warnings": accdb_warnings,
            }
            print(f"  Wrote .accdb to {accdb_path} (template: {template_path})")
        except Exception as exc:
            accdb_result = {"status": "failed", "reason": str(exc), "templatePath": str(template_path)}
            print(f"  .accdb export failed: {exc}")

    return {
        "tables": tables,
        "diagnostics": diagnostics,
        "warnings": warnings,
        "batch_result": batch_result,
        "accdb_result": accdb_result,
    }


def validate_ac_economic(csv_path: Path) -> dict[str, Any]:
    if not csv_path.exists():
        return {"status": "missing", "complete": False, "message": f"Missing: {csv_path}"}
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    keyword_counts: dict[str, int] = {}
    qualifiers: set[str] = set()
    for row in rows:
        keyword = row.get("KEYWORD", "")
        qualifier = row.get("QUALIFIER", "")
        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        if qualifier:
            qualifiers.add(qualifier)
    review_rows = sum(count for kw, count in keyword_counts.items() if kw.startswith("PY_REVIEW"))
    final_rows = len(rows) - review_rows
    return {
        "status": "review_rows_only" if rows and final_rows == 0 else ("mixed_or_final" if rows else "empty"),
        "complete": bool(rows) and final_rows == len(rows),
        "rowCount": len(rows),
        "reviewRowCount": review_rows,
        "finalAriesRowCount": final_rows,
        "qualifiers": sorted(qualifiers),
        "keywordCounts": dict(sorted(keyword_counts.items())),
    }


def validate(pipeline: dict[str, Any]) -> dict[str, Any]:
    from aries_writer import EXPORT_TABLE_ORDER, read_aries_sqlite_tables

    tables = pipeline["tables"]
    errors: list[str] = []

    # Row count checks
    if len(tables["AC_PROPERTY"]) == 0:
        errors.append("AC_PROPERTY is empty")
    if len(tables["AC_PRODUCT"]) == 0:
        errors.append("AC_PRODUCT is empty")

    # PROPNUM referential integrity
    propnums = {row["PROPNUM"] for row in tables["AC_PROPERTY"]}
    for table_name in ["AC_PRODUCT", "AC_ECONOMIC", "AC_OWNER"]:
        for row in tables.get(table_name, []):
            if row.get("PROPNUM") and row["PROPNUM"] not in propnums:
                errors.append(f"Orphan PROPNUM '{row['PROPNUM']}' in {table_name}")
                break

    # PROJLIST integrity
    for row in tables.get("PROJLIST", []):
        match = re.search(r"PROPNUM='([^']+)'", row.get("PROPKEY", ""))
        if match and match.group(1) not in propnums:
            errors.append(f"Orphan PROJLIST: {row['PROPKEY']}")
            break

    # SORTFILTERS TableAlias
    for row in tables.get("SORTFILTERS", []):
        if row.get("TABLEALIAS") != "M":
            errors.append(f"SORTFILTERS TableAlias={row.get('TABLEALIAS')}, expected M")
            break

    # SRC_DB populated
    for row in tables["AC_PROPERTY"]:
        if not row.get("SRC_DB"):
            errors.append("SRC_DB is empty in AC_PROPERTY")
            break

    # AC_PROPERTY standard ARIES columns present
    ac_prop_standard_cols = ["SEQNUM", "FIRST_PROD", "RESCAT", "API", "STATUS"]
    if tables["AC_PROPERTY"]:
        first_prop = tables["AC_PROPERTY"][0]
        for col in ac_prop_standard_cols:
            if col not in first_prop:
                errors.append(f"AC_PROPERTY missing standard column: {col}")

    # AC_SCENARIO has QUAL9 and OWNER columns
    if tables.get("AC_SCENARIO"):
        first_scen = tables["AC_SCENARIO"][0]
        for col in ["QUAL9", "OWNER"]:
            if col not in first_scen:
                errors.append(f"AC_SCENARIO missing column: {col}")
    else:
        errors.append("AC_SCENARIO is empty")

    # AC_SETUP is non-empty and contains TAURIS setup name
    ac_setup_rows = tables.get("AC_SETUP", [])
    if not ac_setup_rows:
        errors.append("AC_SETUP is empty or missing")
    else:
        setup_names = {row.get("SETUPNAME", "") for row in ac_setup_rows}
        if "TAURIS" not in setup_names:
            errors.append("AC_SETUP missing TAURIS setup name")

    # SQLite roundtrip
    aries_sqlite = OUTPUT_DIR / "aries.sqlite"
    roundtrip = read_aries_sqlite_tables(aries_sqlite)
    for table_name in EXPORT_TABLE_ORDER:
        orig = len(tables.get(table_name, []))
        rt = len(roundtrip.get(table_name, []))
        if orig != rt:
            errors.append(f"{table_name} SQLite roundtrip: orig={orig}, restored={rt}")

    # Batched export consistency
    batched = read_aries_sqlite_tables(OUTPUT_DIR / "aries_batched.sqlite")
    for table_name in ["AC_PROPERTY", "AC_PRODUCT", "AC_ECONOMIC"]:
        orig = len(tables.get(table_name, []))
        bt = len(batched.get(table_name, []))
        if orig != bt:
            errors.append(f"{table_name} batched mismatch: orig={orig}, batched={bt}")

    # AC_ECONOMIC validation
    econ_result = validate_ac_economic(OUTPUT_DIR / "aries-csv" / "AC_ECONOMIC.csv")

    # prepare_access_tables
    from aries_writer import prepare_access_tables
    access_tables, access_diag = prepare_access_tables(tables)
    if access_diag["omittedReviewEconomicRows"] > 0:
        print(f"  prepare_access_tables: omitted {access_diag['omittedReviewEconomicRows']} review rows")

    # .accdb validation (when generated)
    accdb_result = pipeline.get("accdb_result", {})
    if accdb_result.get("status") == "ok":
        accdb_path = Path(accdb_result["accdbPath"])
        if not accdb_path.exists():
            errors.append(".accdb file missing after successful write")
        else:
            print(f"  .accdb validated: {accdb_path}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "propertyCount": len(tables["AC_PROPERTY"]),
        "productCount": len(tables["AC_PRODUCT"]),
        "economicRowCount": len(tables["AC_ECONOMIC"]),
        "acEconomicValidation": econ_result,
        "accessPayload": access_diag,
        "accdbExport": accdb_result.get("status", "not_attempted"),
        "errors": errors,
    }
    return result


def main() -> int:
    print("=== PHDWin v2 E2E Test ===")

    print("[1/4] Cleaning outputs...")
    clean_outputs()

    print("[2/4] Resolving source data (.phz -> ODBC -> review SQLite -> synthetic)...")
    source, source_meta = resolve_source()
    print(f"  Source type: {source_meta['sourceType']}")

    print("[3/4] Running pipeline (tables -> CSV -> SQLite -> .accdb)...")
    pipeline = run_pipeline(source)

    print("[4/4] Validating...")
    result = validate(pipeline)
    result["sourceMeta"] = source_meta

    summary_path = OUTPUT_DIR / "e2e_summary.json"
    summary_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    accdb_status = result.get("accdbExport", "not_attempted")
    if result["status"] == "PASS":
        print(f"  PASS: {result['propertyCount']} properties, {result['productCount']} products, {result['economicRowCount']} economic rows, accdb={accdb_status}")
    else:
        print(f"  FAIL: {result['errors']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
