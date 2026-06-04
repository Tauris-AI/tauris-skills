#!/usr/bin/env python3
from __future__ import annotations

from aries_economic import build_ac_economic_rows


def test_missing_required_table() -> None:
    result = build_ac_economic_rows({})
    assert result.rows == []
    assert "PHD_FORCAST" in result.diagnostics["missingRequiredTables"]
    assert any("missing required economic source tables" in warning for warning in result.warnings)


def test_scoped_forecast_count() -> None:
    result = build_ac_economic_rows(
        {
            "PHD_PRODUCTNAMES": [{"PRODUCTCODE": "1", "DESCR": "Oil"}],
            "PHD_FORCAST": [
                {"LSE_ID": "1", "PRODUCTCODE": "1", "QI": "100"},
                {"LSE_ID": "2", "PRODUCTCODE": "2"},
            ],
            "PHD_ECON": [{"LSE_ID": "1", "OPCOST": "12.50"}],
            "PHD_INVEST": [{"LSE_ID": "1", "AMOUNT": "1000", "INVESTDESCR_ID": "7"}],
            "PHD_INVESTDESCR": [{"INVESTDESCR_ID": "7", "DESCR": "Drilling"}],
            "PHD_LSESEGMENT": [{"LSE_ID": "1", "SEG_ID": "3", "QI": "75"}],
            "PHD_LSEPRODVAL": [{"LSE_ID": "1", "PRODUCTCODE": "1", "PRICE": "2.50"}],
            "MOD_SCEN": [{"LSE_ID": "1", "SCEN_ID": "A", "NAME": "Base"}],
            "MOD_TEMPLATE": [{"LSE_ID": "1", "TEMPLATE_ID": "T1", "NAME": "Default"}],
            "PHD_CUMVOL": [{"LSE_ID": "1", "PRODUCTCODE": "1", "CUMOIL": "500"}],
        },
        selected_lease_ids={1},
    )
    assert len(result.rows) == 8
    assert result.rows[0]["PROPNUM"] == "PHD000001"
    assert result.rows[0]["SECTION"] == 1
    assert result.rows[0]["SEQUENCE"] == 1
    assert result.rows[0]["KEYWORD"] == "PY_REVIEW_FORECAST"
    assert "PRODUCTCODE=1" in result.rows[0]["EXPRESSION"]
    assert "PRODUCT_NAME=Oil" in result.rows[0]["EXPRESSION"]
    assert result.rows[1]["KEYWORD"] == "PY_REVIEW_ECON"
    assert "OPCOST=12.50" in result.rows[1]["EXPRESSION"]
    assert result.rows[2]["KEYWORD"] == "PY_REVIEW_INVEST"
    assert "AMOUNT=1000" in result.rows[2]["EXPRESSION"]
    assert "INVEST_DESCRIPTION=Drilling" in result.rows[2]["EXPRESSION"]
    assert result.rows[2]["SOURCE_INVEST_DESCRIPTION"] == "Drilling"
    assert result.rows[3]["KEYWORD"] == "PY_REVIEW_SEGMENT"
    assert "QI=75" in result.rows[3]["EXPRESSION"]
    assert result.rows[4]["KEYWORD"] == "PY_REVIEW_PRODVAL"
    assert "PRICE=2.50" in result.rows[4]["EXPRESSION"]
    assert result.rows[5]["KEYWORD"] == "PY_REVIEW_SCEN"
    assert "NAME=Base" in result.rows[5]["EXPRESSION"]
    assert result.rows[6]["KEYWORD"] == "PY_REVIEW_TEMPLATE"
    assert "NAME=Default" in result.rows[6]["EXPRESSION"]
    assert result.rows[7]["KEYWORD"] == "PY_REVIEW_CUMVOL"
    assert "CUMOIL=500" in result.rows[7]["EXPRESSION"]
    assert result.diagnostics["tableCounts"]["PHD_FORCAST"] == 2
    assert result.diagnostics["scopedTableCounts"]["PHD_FORCAST"] == 1
    assert result.diagnostics["selectedLeaseIds"] == [1]
    assert result.diagnostics["forecastReviewRowCount"] == 1
    assert result.diagnostics["econReviewRowCount"] == 1
    assert result.diagnostics["investReviewRowCount"] == 1
    assert result.diagnostics["segmentReviewRowCount"] == 1
    assert result.diagnostics["prodvalReviewRowCount"] == 1
    assert result.diagnostics["scenarioReviewRowCount"] == 1
    assert result.diagnostics["templateReviewRowCount"] == 1
    assert result.diagnostics["cumvolReviewRowCount"] == 1
    assert result.diagnostics["unmatchedInvestDescriptionCount"] == 0
    assert result.diagnostics["unmatchedProductCodeCounts"]["PHD_FORCAST"] == 0


def test_forecast_ordering() -> None:
    result = build_ac_economic_rows(
        {
            "PHD_FORCAST": [
                {"LSE_ID": "2", "ARCSEQ": "2", "PRODUCTCODE": "1", "QI": "10"},
                {"LSE_ID": "1", "ARCSEQ": "2", "PRODUCTCODE": "1", "QI": "20"},
                {"LSE_ID": "1", "ARCSEQ": "1", "PRODUCTCODE": "2", "QI": "30"},
            ],
        },
    )
    assert [row["PROPNUM"] for row in result.rows] == ["PHD000001", "PHD000001", "PHD000002"]
    assert [row["SOURCE_ARCSEQ"] for row in result.rows] == [1, 2, 2]
    assert [row["SEQUENCE"] for row in result.rows] == [1, 2, 3]


def test_section_sequences_are_independent() -> None:
    result = build_ac_economic_rows(
        {
            "PHD_FORCAST": [{"LSE_ID": "1", "ARCSEQ": "5", "PRODUCTCODE": "1", "QI": "100"}],
            "PHD_ECON": [{"LSE_ID": "1", "SEQ": "7", "OPCOST": "10"}],
            "PHD_INVEST": [{"LSE_ID": "1", "SEQ": "9", "AMOUNT": "500"}],
            "PHD_LSESEGMENT": [{"LSE_ID": "1", "SEQ": "11", "QI": "100"}],
            "PHD_LSEPRODVAL": [{"LSE_ID": "1", "SEQ": "13", "PRICE": "3"}],
            "MOD_SCEN": [{"LSE_ID": "1", "SEQ": "15", "NAME": "Base"}],
            "MOD_TEMPLATE": [{"LSE_ID": "1", "SEQ": "17", "NAME": "Template"}],
            "PHD_CUMVOL": [{"LSE_ID": "1", "SEQ": "19", "CUMOIL": "5"}],
        },
    )
    assert [(row["SECTION"], row["SEQUENCE"]) for row in result.rows] == [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1)]


def test_unmatched_invest_description_count() -> None:
    result = build_ac_economic_rows(
        {
            "PHD_FORCAST": [{"LSE_ID": "1"}],
            "PHD_INVEST": [{"LSE_ID": "1", "INVESTDESCR_ID": "99", "AMOUNT": "500"}],
            "PHD_INVESTDESCR": [{"INVESTDESCR_ID": "1", "DESCR": "Facilities"}],
        },
    )
    assert result.diagnostics["unmatchedInvestDescriptionCount"] == 1
    assert any("no matching PHD_INVESTDESCR" in warning for warning in result.warnings)


def test_rows_without_lease_id_are_skipped() -> None:
    result = build_ac_economic_rows(
        {
            "PHD_FORCAST": [
                {"LSE_ID": "1", "ARCSEQ": "1", "QI": "25"},
                {"ARCSEQ": "2", "QI": "25"},
            ],
            "PHD_ECON": [{"OPCOST": "9"}],
        },
    )
    assert len(result.rows) == 1
    assert result.rows[0]["SOURCE_TABLE"] == "PHD_FORCAST"
    assert result.diagnostics["missingLeaseIdCounts"]["PHD_FORCAST"] == 1
    assert result.diagnostics["missingLeaseIdCounts"]["PHD_ECON"] == 1
    assert any("without usable LSE_ID" in warning for warning in result.warnings)


def test_unmatched_product_code_count() -> None:
    result = build_ac_economic_rows(
        {
            "PHD_PRODUCTNAMES": [{"PRODUCTCODE": "1", "DESCR": "Oil"}],
            "PHD_FORCAST": [{"LSE_ID": "1", "PRODUCTCODE": "9", "QI": "100"}],
            "PHD_LSESEGMENT": [{"LSE_ID": "1", "PRODUCTCODE": "8"}],
            "PHD_LSEPRODVAL": [{"LSE_ID": "1", "PRODUCTCODE": "7"}],
            "PHD_CUMVOL": [{"LSE_ID": "1", "PRODUCTCODE": "6"}],
        },
    )
    assert result.diagnostics["unmatchedProductCodeCounts"]["PHD_FORCAST"] == 1
    assert result.diagnostics["unmatchedProductCodeCounts"]["PHD_LSESEGMENT"] == 1
    assert result.diagnostics["unmatchedProductCodeCounts"]["PHD_LSEPRODVAL"] == 1
    assert result.diagnostics["unmatchedProductCodeCounts"]["PHD_CUMVOL"] == 1
    assert any("product codes missing from PHD_PRODUCTNAMES" in warning for warning in result.warnings)


def main() -> int:
    test_missing_required_table()
    test_scoped_forecast_count()
    test_forecast_ordering()
    test_section_sequences_are_independent()
    test_unmatched_invest_description_count()
    test_rows_without_lease_id_are_skipped()
    test_unmatched_product_code_count()
    print("AC_ECONOMIC diagnostics scaffold tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
