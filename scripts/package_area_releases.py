#!/usr/bin/env python3
"""Build per-area zip files for GitHub Releases."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REPO_ROOT = Path(__file__).resolve().parents[1]
AREAS_ROOT = REPO_ROOT / "areas"
DIST_ROOT = REPO_ROOT / "dist"
DEFAULT_AREAS = ("phdwin-v2", "aries", "petroleum-economics")

EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".mdb",
    ".bak",
}

EXCLUDED_DATA_DIRS = {
    ("data", "original"),
    ("data", "extracted"),
    ("data", "review"),
}

ALLOWED_BINARY_REFERENCES = {
    Path("phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/Aries_Template.accdb"),
    Path("phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/phdwin-v2/Phdwinout definitions_complete.xls"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one release zip per Tauris skill area.")
    parser.add_argument("--version", required=True, help="Release version, for example v1.0.0")
    parser.add_argument(
        "--include-version",
        action="store_true",
        help="Include the version in asset filenames, for example phdwin-v2-v1.0.0.zip.",
    )
    parser.add_argument(
        "--area",
        action="append",
        choices=DEFAULT_AREAS,
        help="Area to package. Repeat for multiple areas. Defaults to all areas.",
    )
    parser.add_argument("--dist", default=str(DIST_ROOT), help="Output directory for zip files.")
    return parser.parse_args()


def should_include(path: Path, area_root: Path, area_name: str) -> bool:
    if not path.is_file():
        return False

    rel_to_area = path.relative_to(area_root)
    rel_to_repo_area = Path(area_name) / rel_to_area

    if any(part in EXCLUDED_PARTS for part in rel_to_area.parts):
        return False

    for parent, child in EXCLUDED_DATA_DIRS:
        parts = rel_to_area.parts
        if parent in parts:
            index = parts.index(parent)
            if index + 1 < len(parts) and parts[index + 1] == child:
                return path.name == ".gitkeep"

    suffix = path.suffix.lower()
    if suffix in EXCLUDED_SUFFIXES and rel_to_repo_area not in ALLOWED_BINARY_REFERENCES:
        return False

    return True


def package_area(area_name: str, version: str, dist_root: Path, include_version: bool) -> Path:
    area_root = AREAS_ROOT / area_name
    if not area_root.exists():
        raise FileNotFoundError(f"Area not found: {area_root}")

    filename = f"{area_name}-{version}.zip" if include_version else f"{area_name}.zip"
    zip_path = dist_root / filename
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(REPO_ROOT / "LICENSE", "LICENSE")
        for path in sorted(area_root.rglob("*")):
            if not should_include(path, area_root, area_name):
                continue
            archive_name = Path(area_name) / path.relative_to(area_root)
            archive.write(path, archive_name.as_posix())
    return zip_path


def main() -> int:
    args = parse_args()
    areas = tuple(args.area or DEFAULT_AREAS)
    dist_root = Path(args.dist).resolve()
    dist_root.mkdir(parents=True, exist_ok=True)

    for area in areas:
        zip_path = package_area(area, args.version, dist_root, args.include_version)
        print(zip_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
