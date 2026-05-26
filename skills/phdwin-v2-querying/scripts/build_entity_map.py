#!/usr/bin/env python3
"""
Build a markdown map of PhdWIN generated entities, routes, and table annotations.

Usage:
    python3 build_entity_map.py /path/to/Tauris.PhdWin
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROUTE_RE = re.compile(r'\[GeneratedController\("([^"]+)"\)\]')
TABLE_RE = re.compile(r'\[.*Table\(@\"([^\"]+)\"\)\]')
CLASS_RE = re.compile(r"public class (\w+)")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 build_entity_map.py /path/to/Tauris.PhdWin", file=sys.stderr)
        return 1

    repo_root = Path(sys.argv[1]).resolve()
    entity_dir = repo_root / "src" / "Tauris.Odbc.Common.Objects" / "GeneratedEntities"
    if not entity_dir.is_dir():
        print(f"GeneratedEntities directory not found: {entity_dir}", file=sys.stderr)
        return 1

    rows: list[tuple[str, str, str, str]] = []
    for path in sorted(entity_dir.glob("*.cs")):
        text = path.read_text(encoding="utf-8")
        route = ROUTE_RE.search(text)
        table = TABLE_RE.search(text)
        klass = CLASS_RE.search(text)
        if not klass or not table:
            continue
        rows.append(
            (
                klass.group(1),
                route.group(1) if route else "",
                table.group(1),
                path.name,
            )
        )

    print("# Generated Entity Map")
    print()
    print("Built from `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Odbc.Common.Objects/GeneratedEntities`.")
    print()
    print("| Entity | Route | Table Annotation | Source File |")
    print("| --- | --- | --- | --- |")
    for entity, route, table, source_file in rows:
        print(f"| `{entity}` | `{route}` | `{table}` | `{source_file}` |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
