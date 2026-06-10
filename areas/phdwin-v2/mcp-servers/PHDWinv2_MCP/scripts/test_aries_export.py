#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
import sqlite3
import tempfile
from pathlib import Path

from aries_export import build_aries_tables, export_aries, prepare_access_tables


def make_sqlite(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE PHD_MAINLSE (LSE_ID TEXT, LSE_NAME TEXT)")
        conn.execute("INSERT INTO PHD_MAINLSE VALUES (?, ?)", ("1", "Sample Lease"))
        conn.execute("CREATE TABLE PHD_GROUPS (GRP_ID TEXT, GRP_DESC TEXT)")
        conn.execute("INSERT INTO PHD_GROUPS VALUES (?, ?)", ("1", "All Cases"))
        conn.execute(
            "CREATE TABLE PHD_OWNER (LSE_ID TEXT, GRP_ID TEXT, SEQ TEXT, RESOLVEDDATE TEXT, LSENRI TEXT, WRKINT TEXT, REVINT TEXT)"
        )
        conn.execute(
            "INSERT INTO PHD_OWNER VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("1", "1", "1", "0", "0.75", "1.0", "0.75"),
        )
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
        conn.execute(
            'CREATE TABLE PHD_MONHIST (LSE_ID TEXT, TYPE TEXT, YEAR TEXT, "PROD1$1" TEXT, "PROD2$1" TEXT, "PROD3$1" TEXT, "PROD4$1" TEXT, "PROD5$1" TEXT)'
        )
        conn.execute(
            'INSERT INTO PHD_MONHIST VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            ("1", "0", "2024", "1200", "45", "3", "1", "31"),
        )
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
        owner_rows = read_csv(output_dir / "csv" / "AC_OWNER.csv")
        scenario_rows = read_csv(output_dir / "csv" / "AC_SCENARIO.csv")
        product_rows = read_csv(output_dir / "csv" / "AC_PRODUCT.csv")

        assert result.table_counts["AC_ECONOMIC"] == 9
        assert result.table_counts["AC_OWNER"] == 3
        assert result.table_counts["AC_PRODUCT"] == 12
        assert property_rows[0]["SRC_DB"] == "source"
        jan_product = next(row for row in product_rows if row["P_DATE"] == "2024.01.31")
        assert jan_product["GAS"] == "1200.0"
        assert jan_product["OIL"] == "45.0"
        assert jan_product["WATER"] == "3.0"
        assert jan_product["WELLCOUNT"] == "1.0"
        assert jan_product["DAYS_ON"] == "31.0"
        assert {row["PHASENAME"] for row in owner_rows} == {"LSE/WI", "NET/OIL", "NET/GAS"}
        assert {row["SCENARIO"] for row in owner_rows} == {"ACTIVE"}
        assert {row["STARTDATE"] for row in owner_rows} == {"2000.01.01"}
        assert {row["OWNERNAME"] for row in owner_rows} == {"ALLCASES"}
        active_rows = [row for row in scenario_rows if row["SCEN_NAME"] == "ACTIVE"]
        assert [row["DATA_SECT"] for row in active_rows] == [str(section) for section in range(1, 10)]
        assert {row["QUAL0"] for row in active_rows} == {"TAURIS"}
        assert {row["QUAL1"] for row in active_rows} == {"PY_REVIEW"}
        assert result.diagnostics is not None
        assert result.diagnostics["acEconomic"]["status"] == "review_rows_only"
        assert result.diagnostics["acEconomic"]["complete"] is False
        assert result.diagnostics["acEconomic"]["reviewRowCount"] == 9
        assert result.diagnostics["acEconomic"]["finalAriesRowCount"] == 0
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


def test_build_aries_tables_reads_phdwin_dollar_month_columns() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="aries-product-test-"))
    try:
        sqlite_path = temp_dir / "source.sqlite"
        make_sqlite(sqlite_path)
        tables, _, _ = build_aries_tables(sqlite_path)
        rows = [row for row in tables["AC_PRODUCT"] if row["PROPNUM"] == "PHD000001"]
        jan = next(row for row in rows if row["P_DATE"] == "2024.01.31")

        assert jan["GAS"] == 1200.0
        assert jan["OIL"] == 45.0
        assert jan["WATER"] == 3.0
        assert jan["WELLCOUNT"] == 1.0
        assert jan["DAYS_ON"] == 31.0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_prepare_access_tables_omits_review_economic_rows() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="aries-access-payload-test-"))
    try:
        sqlite_path = temp_dir / "source.sqlite"
        make_sqlite(sqlite_path)
        tables, _, _ = build_aries_tables(sqlite_path)
        access_tables, diagnostics = prepare_access_tables(tables)

        assert len(tables["AC_ECONOMIC"]) == 9
        assert access_tables["AC_ECONOMIC"] == []
        assert diagnostics["omittedReviewEconomicRows"] == 9
        assert diagnostics["accessEconomicRowCount"] == 0
        assert diagnostics["status"] == "empty"
        active_rows = [row for row in access_tables["AC_SCENARIO"] if row["SCEN_NAME"] == "ACTIVE"]
        assert {row.get("QUAL1", "") for row in active_rows} == {""}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    test_export_writes_forecast_review_rows()
    test_build_aries_tables_reads_phdwin_dollar_month_columns()
    test_prepare_access_tables_omits_review_economic_rows()
    print("Aries export integration tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
