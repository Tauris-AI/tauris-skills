#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


def safe_csv_name(table_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", table_name.strip())
    return cleaned or "table"


def sqlite_tables(sqlite_path: Path) -> list[str]:
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return [str(row[0]) for row in rows]


def export_sqlite_tables_to_csv(
    sqlite_path: Path,
    output_dir: Path,
    tables: list[str] | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    sqlite_path = sqlite_path.resolve()
    output_dir = output_dir.resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

    available = sqlite_tables(sqlite_path)
    available_by_upper = {table.upper(): table for table in available}
    selected = available if not tables else []
    missing: list[str] = []
    if tables:
        for table in tables:
            actual = available_by_upper.get(table.upper())
            if actual:
                selected.append(actual)
            else:
                missing.append(table)

    output_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, Any]] = []
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        for table in selected:
            csv_path = output_dir / f"{safe_csv_name(table)}.csv"
            if csv_path.exists() and not overwrite:
                raise FileExistsError(f"CSV already exists: {csv_path}")
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            columns = [description[0] for description in conn.execute(f'SELECT * FROM "{table}" LIMIT 0').description]
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
            exported.append({"table": table, "csvPath": str(csv_path), "rowCount": len(rows)})

    summary = {
        "sourceSqlite": str(sqlite_path),
        "outputDir": str(output_dir),
        "exported": exported,
        "missingTables": missing,
    }
    with (output_dir / "csv-export-summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SQLite tables to named CSV files.")
    parser.add_argument("sqlite_path", help="SQLite database path")
    parser.add_argument("output_dir", help="Output directory for named CSV files")
    parser.add_argument("--table", action="append", default=[], help="Optional table to export. Repeat for multiple tables.")
    parser.add_argument("--no-overwrite", action="store_true", help="Fail if a CSV already exists.")
    args = parser.parse_args()

    result = export_sqlite_tables_to_csv(
        Path(args.sqlite_path),
        Path(args.output_dir),
        tables=args.table or None,
        overwrite=not args.no_overwrite,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
