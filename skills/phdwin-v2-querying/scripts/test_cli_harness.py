#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CLI = SCRIPT_DIR / "phdwin_cli.py"


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expect:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(f"Expected exit {expect}, got {result.returncode}: {' '.join(args)}")
    return result


def make_phz(path: Path) -> None:
    source_dir = path.parent / "source"
    source_dir.mkdir(parents=True)
    (source_dir / "SAMPLE.phd").write_text("", encoding="utf-8")
    (source_dir / "SAMPLE.mod").write_text("", encoding="utf-8")
    with zipfile.ZipFile(path, "w") as archive:
        archive.write(source_dir / "SAMPLE.phd", "SAMPLE.phd")
        archive.write(source_dir / "SAMPLE.mod", "SAMPLE.mod")


def make_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE PHD_MAINLSE (LSE_ID TEXT, LEASENAME TEXT)")
        conn.execute("INSERT INTO PHD_MAINLSE VALUES (?, ?)", ("1", "Sample Lease"))
        conn.execute("CREATE TABLE PHD_OWNER (OWNERID TEXT, OWNERNAME TEXT)")
        conn.commit()
    finally:
        conn.close()


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"Expected output to contain {expected!r}. Output:\n{text}")


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="phdwin-cli-harness-"))
    try:
        phz_path = temp_dir / "sample.phz"
        extracted_dir = temp_dir / "extracted"
        sqlite_path = temp_dir / "sample.sqlite"

        make_phz(phz_path)
        make_sqlite(sqlite_path)

        help_result = run("--help")
        assert_contains(help_result.stdout, "export-sqlite")

        inspect_phz = run("inspect", str(phz_path))
        assert_contains(inspect_phz.stdout, "Detected type: phz")

        extract_result = run("extract", str(phz_path), "--out", str(extracted_dir))
        assert_contains(extract_result.stdout, ".phd files: ['SAMPLE.phd']")
        assert (extracted_dir / "SAMPLE.phd").exists()
        assert (extracted_dir / "SAMPLE.mod").exists()

        inspect_dataset = run("inspect", str(extracted_dir))
        assert_contains(inspect_dataset.stdout, "Detected type: dataset-folder")
        assert_contains(inspect_dataset.stdout, ".phd: SAMPLE.phd")

        inspect_sqlite = run("inspect", str(sqlite_path))
        assert_contains(inspect_sqlite.stdout, "Detected type: sqlite")
        assert_contains(inspect_sqlite.stdout, "PHD_MAINLSE: 1 row(s)")

        smoke_result = run("smoke", str(extracted_dir), expect=2)
        assert_contains(smoke_result.stdout, "pyodbc is not installed")

        print("CLI harness passed.")
        print(f"Temp workspace: {temp_dir}")
        return 0
    except Exception as exc:
        print(f"CLI harness failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if "--keep-temp" not in sys.argv:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
