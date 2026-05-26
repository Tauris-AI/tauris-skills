#!/usr/bin/env python3
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a PhdWIN .phz package into a dataset folder.")
    parser.add_argument("phz_path", help="Path to the .phz file")
    parser.add_argument(
        "--out",
        help="Output folder. Defaults to a sibling folder named after the archive.",
    )
    args = parser.parse_args()

    phz_path = Path(args.phz_path).resolve()
    if not phz_path.exists():
        print(f"Missing .phz file: {phz_path}")
        return 1
    if phz_path.suffix.lower() != ".phz":
        print(f"Expected a .phz file, got: {phz_path.name}")
        return 1

    out_dir = Path(args.out).resolve() if args.out else phz_path.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(phz_path, "r") as archive:
        archive.extractall(out_dir)

    phd_files = sorted(p.name for p in out_dir.glob("*.phd"))
    mod_files = sorted(p.name for p in out_dir.glob("*.mod"))
    print(f"Extracted to: {out_dir}")
    print(f".phd files: {phd_files or 'none'}")
    print(f".mod files: {mod_files or 'none'}")
    print("Use the extracted folder as the ODBC dataset target, not the .phz file itself.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
