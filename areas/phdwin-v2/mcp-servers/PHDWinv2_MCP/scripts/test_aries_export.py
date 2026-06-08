#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
import sqlite3
import tempfile
from pathlib import Path

from aries_export import export_aries


def make_sqlite(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE PHD_MAINLSE (LSE_ID TEXT, LSE_NAME TEXT)")
        conn.execute("INSERT INTO PHD_MAINLSE VALUES (?, ?)", ("1", "Sample Lease"))
        conn.execute("CREATE TABLE PHD_PRODUCTNAMES (PRODUCTCODE TEXT, DESCR TEXT)")
        conn.execute("INSERT INTO PHD_PRODUCTNAMES VALUES (?, ?)", ("1", "Oil"))
        conn.execute("INSERT INTO PHD_PRODUCTNAMES VALUES (?, ?)", ("2", "Gas"))
        conn.execute(
            "CREATE TABLE PHD_FORCAST (LSE_ID TEXT, ARCSEQ TEXT, PRODUCTCODE TEXT, QI TEXT, DI TEXT)"
        )
        conn.execute("INSERT INTO PHD_FORCAST VALUES (?, ?, ?, ?, ?)", ("1", "2", "1", "100", "0.25"))
        conn.execute("INSERT INTO PHD_FORCAST VALUES (?, ?, ?, ?, ?)", ("1", "1", "2", "50", "0.10"))
        conn.execute("CREATE TABLE PHD_ECON (LSE_ID TEXT, SEQ TEXT, OPCOST TEXT)")
        conn.execute("INSERT INTO PHD_ECON VALUES (?, ?, ?)", ("1", "1", "12.50"))
        conn.execute("CREATE TABLE PHD_INVEST (LSE_ID TEXT, SEQ TEXT, AMOUNT TEXT, INVESTDESCR_ID TEXT)")
        conn.execute("INSERT INTO PHD_INVEST VALUES (?, ?, ?, ?)", ("1", "1", "1000", "7"))
        conn.execute("CREATE TABLE PHD_INVESTDESCR (INVESTDESCR_ID TEXT, DESCR TEXT)")
        conn.execute("INSERT INTO PHD_INVESTDESCR VALUES (?, ?)", ("7", "Drilling"))
        conn.execute("CREATE TABLE PHD_LSESEGMENT (LSE_ID TEXT, SEQ TEXT, QI TEXT)")
        conn.execute("INSERT INTO PHD_LSESEGMENT VALUES (?, ?, ?)", ("1", "1", "75"))
        conn.execute("CREATE TABLE PHD_LSEPRODVAL (LSE_ID TEXT, SEQ TEXT, PRICE TEXT)")
        conn.execute("INSERT INTO PHD_LSEPRODVAL VALUES (?, ?, ?)", ("1", "1", "2.50"))
        conn.execute("CREATE TABLE MOD_SCEN (LSE_ID TEXT, SEQ TEXT, NAME TEXT)")
        conn.execute("INSERT INTO MOD_SCEN VALUES (?, ?, ?)", ("1", "1", "Base"))
        conn.execute("CREATE TABLE MOD_TEMPLATE (LSE_ID TEXT, SEQ TEXT, NAME TEXT)")
        conn.execute("INSERT INTO MOD_TEMPLATE VALUES (?, ?, ?)", ("1", "1", "Default"))
        conn.execute("CREATE TABLE PHD_CUMVOL (LSE_ID TEXT, SEQ TEXT, PRODUCTCODE TEXT, CUMOIL TEXT)")
        conn.execute("INSERT INTO PHD_CUMVOL VALUES (?, ?, ?, ?)", ("1", "1", "1", "500"))
        conn.commit()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_export_writes_forecast_review_rows() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="aries-export-test-"))
    try:
        sqlite_path = temp_dir / "source.sqlite"
        output_dir = temp_dir / "out"
        make_sqlite(sqlite_path)

        result = export_aries(sqlite_path, output_dir)
        rows = read_csv(output_dir / "csv" / "AC_ECONOMIC.csv")
        property_rows = read_csv(output_dir / "csv" / "AC_PROPERTY.csv")
        scenario_rows = read_csv(output_dir / "csv" / "AC_SCENARIO.csv")

        assert result.table_counts["AC_ECONOMIC"] == 9
        assert property_rows[0]["SRC_DB"] == "source"
        active_rows = [row for row in scenario_rows if row["SCEN_NAME"] == "ACTIVE"]
        assert [row["DATA_SECT"] for row in active_rows] == [str(section) for section in range(1, 10)]
        assert {row["QUAL0"] for row in active_rows} == {"TAURIS"}
        assert result.diagnostics is not None
        assert result.diagnostics["acEconomic"]["forecastReviewRowCount"] == 2
        assert result.diagnostics["acEconomic"]["econReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["investReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["segmentReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["prodvalReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["scenarioReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["templateReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["cumvolReviewRowCount"] == 1
        assert result.diagnostics["acEconomic"]["unmatchedInvestDescriptionCount"] == 0
        assert result.diagnostics["acEconomic"]["productNameCount"] == 2
        assert result.diagnostics["acEconomic"]["unmatchedProductCodeCounts"]["PHD_FORCAST"] == 0
        forecast_rows = [row for row in rows if row["KEYWORD"] == "PY_REVIEW_FORECAST"]
        assert [row["SEQUENCE"] for row in forecast_rows] == ["1", "2"]
        assert [row["SOURCE_ARCSEQ"] for row in forecast_rows] == ["1", "2"]
        assert "QI=50" in rows[0]["EXPRESSION"]
        assert "PRODUCT_NAME=Gas" in rows[0]["EXPRESSION"]
        assert "DI=0.25" in rows[1]["EXPRESSION"]
        assert "PRODUCT_NAME=Oil" in rows[1]["EXPRESSION"]
        assert any(row["KEYWORD"] == "PY_REVIEW_ECON" and "OPCOST=12.50" in row["EXPRESSION"] for row in rows)
        assert any(row["KEYWORD"] == "PY_REVIEW_INVEST" and "INVEST_DESCRIPTION=Drilling" in row["EXPRESSION"] for row in rows)
        assert any(row["KEYWORD"] == "PY_REVIEW_SEGMENT" and "QI=75" in row["EXPRESSION"] for row in rows)
        assert any(row["KEYWORD"] == "PY_REVIEW_PRODVAL" and "PRICE=2.50" in row["EXPRESSION"] for row in rows)
        assert any(row["KEYWORD"] == "PY_REVIEW_SCEN" and "NAME=Base" in row["EXPRESSION"] for row in rows)
        assert any(row["KEYWORD"] == "PY_REVIEW_TEMPLATE" and "NAME=Default" in row["EXPRESSION"] for row in rows)
        assert any(row["KEYWORD"] == "PY_REVIEW_CUMVOL" and "CUMOIL=500" in row["EXPRESSION"] for row in rows)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    test_export_writes_forecast_review_rows()
    print("Aries export integration tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
