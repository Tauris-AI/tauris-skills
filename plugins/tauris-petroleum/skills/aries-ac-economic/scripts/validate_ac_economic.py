#!/usr/bin/env python3
"""Baseline hygiene validator for sanitized ARIES AC_ECONOMIC examples."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate basic hygiene for sanitized AC_ECONOMIC line examples."
    )
    parser.add_argument("path", help="Text file containing one AC_ECONOMIC example per line")
    return parser.parse_args()


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path} is not a file"]

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        errors.append("file is empty")

    for index, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"line {index}: blank line")
        if "\t" in line:
            errors.append(f"line {index}: contains a tab character")
        if any(ord(char) < 32 and char not in "\r\n\t" for char in line):
            errors.append(f"line {index}: contains a control character")

    return errors


def main() -> None:
    args = parse_args()
    errors = validate(Path(args.path))
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print("AC_ECONOMIC baseline validation passed")


if __name__ == "__main__":
    main()
