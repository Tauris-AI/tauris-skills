#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import date, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "areas/forecasting/mcp-servers/forecasting-mcp"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from forecasting_mcp import convert_decline_convention, profile_and_recommend, validate_industry_alignment  # noqa: E402
from generate_forecasting_sample_plots import load_chart_config, render_svg  # noqa: E402


def test_profile_and_recommend_detects_pressure_and_multiple_origins() -> None:
    with tempfile.TemporaryDirectory(prefix="forecasting-mcp-test-") as tmp:
        path = Path(tmp) / "production.csv"
        start = date(2026, 1, 1)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["WellName", "Date", "Oil", "CasingPressure", "FlowingTubingPressure"],
            )
            writer.writeheader()
            for day in range(90):
                oil = 100 - day * 0.35
                if day >= 30:
                    oil += 80
                if day >= 65:
                    oil += 90
                writer.writerow(
                    {
                        "WellName": "Well A",
                        "Date": (start + timedelta(days=day)).isoformat(),
                        "Oil": f"{oil:.2f}",
                        "CasingPressure": 1000 - day * 5,
                        "FlowingTubingPressure": 760 - day * 3,
                    }
                )

        result = profile_and_recommend(str(path))
        assert result["wellCount"] == 1
        profile = result["profiles"][0]
        assert profile["cadence"]["cadence"] == "daily"
        assert "casing_pressure" in profile["usablePressure"]
        uplifts = [item for item in profile["fitOriginCandidates"] if item["type"] == "sustained_rate_uplift"]
        assert len(uplifts) >= 2
        diagnostics = profile["pressureProjectionDiagnostics"]
        assert any(item["interpretation"] == "drawdown_or_recompletion_response" for item in diagnostics)
        recommendation = result["recommendations"][0]
        alignment = result["industryAlignments"][0]
        assert recommendation["qc"] == "yellow"
        assert recommendation["recommendedMethod"] == "pressure_aware_review_then_arps_hyp_to_exp"
        assert any("drawdown change" in reason for reason in recommendation["reasons"])
        assert any("limited-data" in reason for reason in recommendation["reasons"])
        assert alignment["notComplianceClaim"] is True
        assert alignment["overall"] == "aligned_with_review_flags"


def test_decline_convention_conversion_uses_effective_annual_values() -> None:
    result = convert_decline_convention(
        nominal_di=0.002,
        b_factor=1.2,
        terminal_dmin=0.0002,
        input_time_unit="day",
    )
    assert result["pinnedTimeUnit"] == "year"
    assert result["declineUnit"] == "percent"
    assert result["entryValues"]["initialDecline"] == round(
        (1 - (1 + 1.2 * (0.002 * 365.25)) ** (-1 / 1.2)) * 100,
        6,
    )
    assert result["entryValues"]["terminalDecline"] == round((1 - __import__("math").exp(-(0.0002 * 365.25))) * 100, 6)


def test_sample_plot_renderer_returns_svg() -> None:
    rows = []
    start = date(2024, 1, 1)
    for day in range(30):
        rows.append(
            {
                "Entity Name": "SYNTH TEST PLOT",
                "Date": (start + timedelta(days=day)).strftime("%m/%d/%Y"),
                "OIL - Resolver": f"{900 - day * 12:.3f}",
                "GAS - Resolver": f"{1500 + day * 8:.3f}",
                "WATER - Resolver": f"{220 + day * 1.5:.3f}",
                "Well.Pressure.Casing - Resolver": f"{3200 - day * 9:.3f}",
                "Well.Pressure.Tubing - Resolver": f"{2300 - day * 7:.3f}",
                "Well.Pressure.PumpIntake - Resolver": f"{1800 - day * 4:.3f}",
                "Synthetic.EventType": "normal",
            }
        )
    profile = {
        "fitOriginCandidates": [{"date": "2024-01-01", "type": "first_positive_production"}],
        "pressureProjectionDiagnostics": [{"interpretation": "depletion_supported"}],
    }
    recommendation = {
        "qc": "green",
        "recommendedMethod": "pressure_aware_review_then_arps_hyp_to_exp",
        "reasons": ["Synthetic plot smoke test."],
    }
    config = load_chart_config(REPO_ROOT / "areas/forecasting/mcp-servers/forecasting-mcp/chart_config.default.json")
    svg = render_svg("SYNTH TEST PLOT", rows, profile, recommendation, config=config)
    assert svg.startswith("<svg")
    assert "SYNTH TEST PLOT" in svg
    assert "Arps hyp-to-exp" in svg
    assert "GOR" in svg
    assert "WOR" in svg
    assert "Forecast parameters (" in svg
    assert "Cumulative volumes" in svg
    assert "EUR" in svg
    assert "stroke-dasharray=\"10 6\"" in svg


def test_industry_alignment_validation_avoids_compliance_claim() -> None:
    profile = {
        "well": "Alignment Well",
        "rowCount": 400,
        "cadence": {"cadence": "daily"},
        "usablePressure": ["casing_pressure"],
        "fitOriginCandidates": [{"date": "2024-01-01", "type": "first_positive_production"}],
        "pressureProjectionDiagnostics": [{"interpretation": "depletion_supported"}],
    }
    recommendation = {
        "qc": "green",
        "eligibleMethods": [{"method": "pressure_aware_hybrid_residual"}],
        "notEligibleMethods": [],
    }
    result = validate_industry_alignment(profile, recommendation)
    assert result["notComplianceClaim"] is True
    assert result["alignmentProfile"] == "industry_limited_data_dca"
    assert "not a formal compliance claim" in result["statement"]


def main() -> int:
    test_profile_and_recommend_detects_pressure_and_multiple_origins()
    test_decline_convention_conversion_uses_effective_annual_values()
    test_sample_plot_renderer_returns_svg()
    test_industry_alignment_validation_avoids_compliance_claim()
    print("Forecasting MCP tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
