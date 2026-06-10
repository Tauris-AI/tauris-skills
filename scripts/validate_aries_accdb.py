#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_TABLES = [
    "AC_PROPERTY",
    "AC_OWNER",
    "AC_PRODUCT",
    "AC_TEST",
    "AC_ECONOMIC",
    "PROJECT",
    "PROJLIST",
    "SORTFILTERS",
    "SelFilters",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_aries_mcp() -> Any:
    mcp_dir = repo_root() / "areas" / "aries" / "mcp-servers" / "aries-mcp"
    sys.path.insert(0, str(mcp_dir))
    import aries_mcp  # type: ignore

    return aries_mcp


def extract_propnum(value: Any) -> str:
    text = "" if value is None else str(value)
    match = re.search(r"PROPNUM\s*=\s*'([^']+)'", text, re.IGNORECASE)
    return match.group(1) if match else text


def query_count(aries_mcp: Any, db: str, sql: str) -> int:
    rows = aries_mcp.query(db, sql)
    if not rows:
        return 0
    return int(rows[0].get("n") or 0)


def validate_accdb(db_path: Path, required_tables: list[str]) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"Missing Aries database: {db_path}")

    aries_mcp = load_aries_mcp()
    db = str(db_path)
    available_tables = {table.upper(): table for table in aries_mcp.list_tables(db)}
    missing_tables = [table for table in required_tables if table.upper() not in available_tables]
    counts = {
        table: aries_mcp.query(db, f"SELECT COUNT(*) AS n FROM [{table}]")[0]["n"]
        for table in required_tables
        if table.upper() in available_tables
    }
    empty_required = [
        table
        for table in ("AC_PROPERTY", "AC_OWNER", "PROJECT", "PROJLIST")
        if table in counts and int(counts[table]) <= 0
    ]
    owner_sample = []
    if "AC_OWNER" in available_tables:
        owner_sample = aries_mcp.query(
            db,
            "SELECT TOP 10 PROPNUM, SCENARIO, PHASENAME, STARTDATE, OWNERNAME, INTEREST "
            "FROM [AC_OWNER] ORDER BY PROPNUM, PHASENAME",
        )
    integrity = {"orphanCounts": {}, "scenarioQualifierOrphans": []}
    propnums = {
        str(row["PROPNUM"])
        for row in aries_mcp.query(db, "SELECT PROPNUM FROM [AC_PROPERTY]")
        if row.get("PROPNUM") not in {None, ""}
    } if "AC_PROPERTY" in available_tables else set()
    for table in ("AC_ECONOMIC", "AC_PRODUCT", "AC_TEST", "AC_DAILY", "AC_OWNER"):
        if table not in available_tables:
            continue
        rows = aries_mcp.query(db, f"SELECT PROPNUM FROM [{table}]")
        integrity["orphanCounts"][table] = len({
            str(row["PROPNUM"])
            for row in rows
            if row.get("PROPNUM") not in {None, ""} and str(row["PROPNUM"]) not in propnums
        })
    if "PROJLIST" in available_tables:
        rows = aries_mcp.query(db, "SELECT PROPKEY FROM [PROJLIST]")
        integrity["orphanCounts"]["PROJLIST"] = len({
            extract_propnum(row["PROPKEY"])
            for row in rows
            if row.get("PROPKEY") not in {None, ""}
            and extract_propnum(row["PROPKEY"]) not in propnums
        })

    ac_economic = {
        "status": "not_present",
        "rowCount": 0,
        "reviewRowCount": 0,
        "finalAriesRowCount": 0,
        "complete": False,
    }
    if "AC_ECONOMIC" in available_tables:
        row_count = query_count(aries_mcp, db, "SELECT COUNT(*) AS n FROM [AC_ECONOMIC]")
        review_count = query_count(
            aries_mcp,
            db,
            "SELECT COUNT(*) AS n FROM [AC_ECONOMIC] WHERE [QUALIFIER] = 'PY_REVIEW'",
        )
        final_count = row_count - review_count
        if review_count and final_count:
            status = "mixed_review_and_final"
        elif review_count:
            status = "review_rows_only"
        elif final_count:
            status = "final_rows_present"
        else:
            status = "empty"
        ac_economic = {
            "status": status,
            "rowCount": row_count,
            "reviewRowCount": review_count,
            "finalAriesRowCount": final_count,
            "complete": status == "final_rows_present",
        }

    has_orphans = any(count for count in integrity["orphanCounts"].values())

    return {
        "dbPath": str(db_path),
        "missingTables": missing_tables,
        "emptyRequiredTables": empty_required,
        "counts": counts,
        "acEconomic": ac_economic,
        "integrity": integrity,
        "ownerSample": owner_sample,
        "status": "pass" if not missing_tables and not empty_required and not has_orphans else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated Aries .accdb through the Aries MCP module.")
    parser.add_argument("accdb_path", help="Path to the generated Aries .accdb or .mdb.")
    parser.add_argument("--table", action="append", default=[], help="Required table to validate. May be repeated.")
    args = parser.parse_args()

    required_tables = args.table or DEFAULT_TABLES
    result = validate_accdb(Path(args.accdb_path), required_tables)
    print(json.dumps(result, default=str, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
