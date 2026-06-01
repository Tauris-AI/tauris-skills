#!/usr/bin/env python3
"""
Build a markdown map of PhdWIN generated entities, routes, and table annotations.

Usage:
    python3 build_entity_map.py /path/to/phdwin-implementation
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
        print("Usage: python3 build_entity_map.py /path/to/phdwin-implementation", file=sys.stderr)
        return 1

    repo_root = Path(sys.argv[1]).resolve()
    candidates = sorted(repo_root.glob("src/*/GeneratedEntities"))
    entity_dir = candidates[0] if candidates else None
    if entity_dir is None or not entity_dir.is_dir():
        print("GeneratedEntities directory not found under src/*/GeneratedEntities", file=sys.stderr)
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
    print("Built from the local PhdWIN implementation generated-entity source folder.")
    print()
    print("| Entity | Route | Table Annotation | Source File |")
    print("| --- | --- | --- | --- |")
    for entity, route, table, source_file in rows:
        print(f"| `{entity}` | `{route}` | `{table}` | `{source_file}` |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
