#!/usr/bin/env python3
"""Run all area E2E tests and report results.

Restarts from scratch: each area runner cleans its own outputs.

Usage:
    python e2e-local/run_all_e2e.py
    python e2e-local/run_all_e2e.py --area phdwin-v2
    python e2e-local/run_all_e2e.py --area forecasting --area aries
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

E2E_DIR = Path(__file__).resolve().parent

AREA_RUNNERS = {
    "phdwin-v2": E2E_DIR / "phdwin-v2" / "run_phdwin_e2e.py",
    "forecasting": E2E_DIR / "forecasting" / "run_forecasting_e2e.py",
    "aries": E2E_DIR / "aries" / "run_aries_e2e.py",
}


def load_runner(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"e2e_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all area E2E tests.")
    parser.add_argument(
        "--area",
        action="append",
        choices=list(AREA_RUNNERS.keys()),
        help="Run specific area(s). Defaults to all.",
    )
    args = parser.parse_args()
    areas = args.area or list(AREA_RUNNERS.keys())

    results: dict[str, str] = {}
    exit_code = 0

    for area in areas:
        runner_path = AREA_RUNNERS[area]
        if not runner_path.exists():
            print(f"\n{'='*50}")
            print(f"SKIP: {area} (runner not found: {runner_path})")
            results[area] = "SKIP"
            continue

        print(f"\n{'='*50}")
        try:
            module = load_runner(area, runner_path)
            rc = module.main()
            results[area] = "PASS" if rc == 0 else "FAIL"
            if rc != 0:
                exit_code = 1
        except Exception as exc:
            print(f"  ERROR: {exc}")
            results[area] = f"ERROR: {exc}"
            exit_code = 1

    print(f"\n{'='*50}")
    print("E2E Summary:")
    for area, status in results.items():
        indicator = "PASS" if status == "PASS" else ("SKIP" if status == "SKIP" else "FAIL")
        print(f"  {area:25s} {indicator}")

    if exit_code == 0:
        print("\nAll E2E tests passed.")
    else:
        print("\nSome E2E tests failed.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
