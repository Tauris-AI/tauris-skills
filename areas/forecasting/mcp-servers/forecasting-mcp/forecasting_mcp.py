#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import Any

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - depends on client machine setup
    class FastMCP:  # type: ignore[no-redef]
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self):
            def decorator(func):
                return func

            return decorator

        def run(self) -> None:
            raise SystemExit("fastmcp is not installed. Install with: python -m pip install fastmcp")


mcp = FastMCP("forecasting-mcp")

WELL_ALIASES = ("well", "wellname", "well_name", "wellid", "well_id", "entityname", "entity_name", "api", "api10", "api14")
DATE_ALIASES = ("date", "prod_date", "production_date", "month", "period")
OIL_ALIASES = ("oil", "oilresolver", "oil_rate", "oilrate", "oilbbl", "oil_bbl", "oilvolume", "oil_volume")
GAS_ALIASES = ("gas", "gasresolver", "gas_rate", "gasrate", "gasmcf", "gas_mcf", "gasvolume", "gas_volume")
WATER_ALIASES = ("water", "waterresolver", "water_rate", "waterrate", "waterbbl", "water_bbl", "water_volume")
CASING_PRESSURE_ALIASES = (
    "casingpressure",
    "casing_pressure",
    "wellpressurecasingresolver",
    "well_pressure_casing",
    "cp",
    "csgpressure",
    "csg_pressure",
)
TUBING_PRESSURE_ALIASES = (
    "flowingtubingpressure",
    "flowing_tubing_pressure",
    "tubingpressure",
    "tubing_pressure",
    "wellpressuretubingresolver",
    "well_pressure_tubing",
    "ftp",
    "tp",
)
PUMP_INLET_PRESSURE_ALIASES = (
    "pumpinletpressure",
    "pump_inlet_pressure",
    "pumpintakepressure",
    "pump_intake_pressure",
    "wellpressurepumpintakeresolver",
    "well_pressure_pumpintake",
    "pip",
)

TIME_UNIT_TO_YEARS = {
    "day": 1.0 / 365.25,
    "days": 1.0 / 365.25,
    "daily": 1.0 / 365.25,
    "month": 1.0 / 12.0,
    "months": 1.0 / 12.0,
    "monthly": 1.0 / 12.0,
    "year": 1.0,
    "years": 1.0,
    "annual": 1.0,
}


@dataclass(frozen=True)
class ColumnMap:
    well: str
    date: str
    oil: str | None = None
    gas: str | None = None
    water: str | None = None
    casing_pressure: str | None = None
    tubing_pressure: str | None = None
    pump_inlet_pressure: str | None = None


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _find_column(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    by_norm = {_norm(column): column for column in columns}
    for alias in aliases:
        match = by_norm.get(_norm(alias))
        if match:
            return match
    return None


def _infer_columns(columns: list[str]) -> ColumnMap:
    well = _find_column(columns, WELL_ALIASES)
    dt = _find_column(columns, DATE_ALIASES)
    if not well or not dt:
        raise ValueError(
            "Could not infer well/date columns. Expected well aliases "
            f"{WELL_ALIASES} and date aliases {DATE_ALIASES}."
        )
    return ColumnMap(
        well=well,
        date=dt,
        oil=_find_column(columns, OIL_ALIASES),
        gas=_find_column(columns, GAS_ALIASES),
        water=_find_column(columns, WATER_ALIASES),
        casing_pressure=_find_column(columns, CASING_PRESSURE_ALIASES),
        tubing_pressure=_find_column(columns, TUBING_PRESSURE_ALIASES),
        pump_inlet_pressure=_find_column(columns, PUMP_INLET_PRESSURE_ALIASES),
    )


def _parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    formats = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%Y-%m", "%m/%Y")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _nominal_to_annual(nominal_decline: float, input_time_unit: str) -> float:
    unit = input_time_unit.strip().lower()
    years_per_unit = TIME_UNIT_TO_YEARS.get(unit)
    if years_per_unit is None:
        raise ValueError(f"Unsupported time unit: {input_time_unit}. Expected day, month, or year.")
    if years_per_unit <= 0:
        raise ValueError("Time unit conversion must be positive.")
    return nominal_decline / years_per_unit


def _effective_secant_initial(nominal_di_annual: float, b_factor: float) -> float:
    if nominal_di_annual < 0:
        raise ValueError("Nominal initial decline must be non-negative.")
    if b_factor < 0:
        raise ValueError("B factor must be non-negative.")
    if abs(b_factor) < 1e-12:
        return 1.0 - math.exp(-nominal_di_annual)
    denominator = 1.0 + b_factor * nominal_di_annual
    if denominator <= 0:
        raise ValueError("Invalid hyperbolic denominator from nominal Di and B.")
    return 1.0 - denominator ** (-1.0 / b_factor)


def _effective_exponential_annual(nominal_decline_annual: float) -> float:
    if nominal_decline_annual < 0:
        raise ValueError("Nominal terminal decline must be non-negative.")
    return 1.0 - math.exp(-nominal_decline_annual)


def _signal_profile(values: list[float | None], row_count: int) -> dict[str, Any]:
    present = [value for value in values if value is not None]
    coverage = len(present) / row_count if row_count else 0.0
    positive = [value for value in present if value > 0]
    return {
        "points": len(present),
        "coverage": round(coverage, 4),
        "positivePoints": len(positive),
        "min": min(present) if present else None,
        "max": max(present) if present else None,
        "latest": present[-1] if present else None,
        "isUsable": coverage >= 0.5 and len(positive) >= 6,
    }


def _cadence(dates: list[date]) -> dict[str, Any]:
    ordered = sorted(set(dates))
    if len(ordered) < 2:
        return {"cadence": "unknown", "medianDays": None}
    gaps = [(ordered[i] - ordered[i - 1]).days for i in range(1, len(ordered)) if ordered[i] > ordered[i - 1]]
    if not gaps:
        return {"cadence": "unknown", "medianDays": None}
    med = median(gaps)
    if med <= 3:
        label = "daily"
    elif med <= 10:
        label = "weekly"
    elif med <= 45:
        label = "monthly"
    else:
        label = "sparse"
    return {"cadence": label, "medianDays": med}


def _trend(values: list[float | None]) -> str:
    present = [value for value in values if value is not None and value > 0]
    if len(present) < 6:
        return "unknown"
    split = max(1, len(present) // 3)
    early = median(present[:split])
    late = median(present[-split:])
    if early <= 0:
        return "unknown"
    ratio = late / early
    if ratio < 0.75:
        return "declining"
    if ratio > 1.15:
        return "increasing"
    return "flat"


def _early_late_ratio(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None and value > 0]
    if len(present) < 6:
        return None
    split = max(1, len(present) // 3)
    early = median(present[:split])
    late = median(present[-split:])
    if early <= 0:
        return None
    return late / early


def _volatility(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None and value > 0]
    if len(present) < 6:
        return None
    diffs = [abs(present[i] - present[i - 1]) / max(present[i - 1], 1.0) for i in range(1, len(present))]
    return median(diffs) if diffs else None


def _first_positive_index(values: list[float | None]) -> int | None:
    for index, value in enumerate(values):
        if value is not None and value > 0:
            return index
    return None


def _rolling_median(values: list[float], index: int, width: int) -> float | None:
    start = max(0, index - width)
    end = min(len(values), index + width + 1)
    sample = [value for value in values[start:end] if value > 0]
    return median(sample) if sample else None


def _is_far_enough(index: int, accepted: list[int], min_gap: int) -> bool:
    return all(abs(index - prior) >= min_gap for prior in accepted)


def _origin_candidates(dates: list[date], rows: list[dict[str, Any]], columns: ColumnMap) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    production_columns = [
        ("oil", columns.oil),
        ("gas", columns.gas),
        ("water", columns.water),
    ]
    pressure_columns = [
        ("casing_pressure", columns.casing_pressure),
        ("tubing_pressure", columns.tubing_pressure),
        ("pump_inlet_pressure", columns.pump_inlet_pressure),
    ]

    best_first: tuple[int, str] | None = None
    for phase, column in production_columns:
        if not column:
            continue
        values = [_parse_float(row.get(column)) for row in rows]
        index = _first_positive_index(values)
        if index is not None and (best_first is None or index < best_first[0]):
            best_first = (index, phase)

    if best_first is not None:
        index, phase = best_first
        candidates.append(
            {
                "date": dates[index].isoformat(),
                "type": "first_positive_production",
                "confidence": "medium",
                "reason": f"First positive {phase} production in the dataset.",
            }
        )

    for phase, column in production_columns:
        if not column:
            continue
        values = [_parse_float(row.get(column)) for row in rows]
        numeric = [value if value is not None else 0.0 for value in values]
        if len(numeric) < 12:
            continue
        accepted_indexes: list[int] = []
        min_gap = max(7, len(numeric) // 12)
        for index in range(4, len(numeric) - 3):
            before = _rolling_median(numeric, index - 2, 3)
            after = _rolling_median(numeric, index + 2, 3)
            if before and after and before > 0 and after / before >= 1.5 and _is_far_enough(index, accepted_indexes, min_gap):
                accepted_indexes.append(index)
                candidates.append(
                    {
                        "date": dates[index].isoformat(),
                        "type": "sustained_rate_uplift",
                        "phase": phase,
                        "ratio": round(after / before, 3),
                        "confidence": "medium",
                        "reason": f"{phase} rolling median increased by at least 50%; possible recompletion, stimulation, cleanup, or operating change.",
                    }
                )
                if len(accepted_indexes) >= 4:
                    break

    for signal, column in pressure_columns:
        if not column:
            continue
        values = [_parse_float(row.get(column)) for row in rows]
        numeric = [value if value is not None else 0.0 for value in values]
        if len([value for value in values if value is not None]) < 12:
            continue
        accepted_indexes = []
        min_gap = max(7, len(numeric) // 12)
        for index in range(4, len(numeric) - 3):
            before = _rolling_median(numeric, index - 2, 3)
            after = _rolling_median(numeric, index + 2, 3)
            if (
                before
                and after
                and abs(after - before) / max(abs(before), 1.0) >= 0.35
                and _is_far_enough(index, accepted_indexes, min_gap)
            ):
                accepted_indexes.append(index)
                candidates.append(
                    {
                        "date": dates[index].isoformat(),
                        "type": "pressure_step_change",
                        "signal": signal,
                        "relativeChange": round((after - before) / max(abs(before), 1.0), 3),
                        "confidence": "low",
                        "reason": f"{signal} shifted materially; use as context for fit-window selection, not as a standalone forecast origin.",
                    }
                )
                if len(accepted_indexes) >= 4:
                    break

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate["date"], candidate["type"])
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped[:6]


def _pressure_projection_diagnostics(rows: list[dict[str, Any]], columns: ColumnMap) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    production_columns = [
        ("oil", columns.oil),
        ("gas", columns.gas),
        ("water", columns.water),
    ]
    pressure_columns = [
        ("casing_pressure", columns.casing_pressure),
        ("tubing_pressure", columns.tubing_pressure),
        ("pump_inlet_pressure", columns.pump_inlet_pressure),
    ]

    pressure_values: dict[str, list[float | None]] = {
        signal: [_parse_float(row.get(column)) for row in rows]
        for signal, column in pressure_columns
        if column
    }
    usable_pressure = {
        signal: values
        for signal, values in pressure_values.items()
        if _signal_profile(values, len(rows))["isUsable"]
    }
    if not usable_pressure:
        return diagnostics

    for phase, column in production_columns:
        if not column:
            continue
        rate_values = [_parse_float(row.get(column)) for row in rows]
        rate_profile = _signal_profile(rate_values, len(rows))
        if not rate_profile["isUsable"]:
            continue
        rate_ratio = _early_late_ratio(rate_values)
        if rate_ratio is None:
            continue
        rate_trend = _trend(rate_values)
        rate_volatility = _volatility(rate_values) or 0.0

        for pressure_signal, values in usable_pressure.items():
            pressure_ratio = _early_late_ratio(values)
            if pressure_ratio is None:
                continue
            pressure_trend = _trend(values)
            pressure_volatility = _volatility(values) or 0.0

            if rate_trend == "declining" and pressure_trend == "declining":
                interpretation = "depletion_supported"
                projection_guidance = "Decline fit is more likely to reflect reservoir depletion; constrained Arps candidates are appropriate."
                confidence = "medium"
            elif rate_trend == "declining" and pressure_trend in {"flat", "increasing"}:
                interpretation = "possible_constraint_or_operational_issue"
                projection_guidance = "Avoid fitting recent rate loss as pure depletion until constraint, lift, downtime, choke, or facility effects are reviewed."
                confidence = "medium"
            elif rate_trend == "increasing" and pressure_trend == "declining":
                interpretation = "drawdown_or_recompletion_response"
                projection_guidance = "Test a new forecast origin after the rate increase; full-history fitting may be misleading."
                confidence = "medium"
            elif rate_trend == "flat" and pressure_trend == "declining":
                interpretation = "hidden_depletion_risk"
                projection_guidance = "Rate history looks stable but falling pressure suggests future decline risk; keep QC at least yellow."
                confidence = "low"
            elif rate_volatility >= 0.25 and pressure_volatility >= 0.15:
                interpretation = "operationally_unstable"
                projection_guidance = "High rate and pressure volatility indicate unstable operations; route to human review or robust/simple fit windows."
                confidence = "low"
            else:
                interpretation = "pressure_context_available"
                projection_guidance = "Pressure is available but does not strongly classify the projection; use as QC context."
                confidence = "low"

            diagnostics.append(
                {
                    "phase": phase,
                    "pressureSignal": pressure_signal,
                    "interpretation": interpretation,
                    "confidence": confidence,
                    "rateTrend": rate_trend,
                    "pressureTrend": pressure_trend,
                    "rateEarlyLateRatio": round(rate_ratio, 4),
                    "pressureEarlyLateRatio": round(pressure_ratio, 4),
                    "rateVolatility": round(rate_volatility, 4),
                    "pressureVolatility": round(pressure_volatility, 4),
                    "projectionGuidance": projection_guidance,
                }
            )
    return diagnostics


def _load_csv(csv_path: str) -> tuple[ColumnMap, dict[str, list[dict[str, Any]]]]:
    path = Path(csv_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        columns = _infer_columns(reader.fieldnames)
        by_well: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in reader:
            well = str(row.get(columns.well, "")).strip()
            dt = _parse_date(row.get(columns.date, ""))
            if not well or not dt:
                continue
            by_well[well].append({"date": dt, "row": row})
    return columns, dict(by_well)


def _profile_well(well: str, records: list[dict[str, Any]], columns: ColumnMap) -> dict[str, Any]:
    records = sorted(records, key=lambda item: item["date"])
    rows = [item["row"] for item in records]
    dates = [item["date"] for item in records]

    signals: dict[str, dict[str, Any]] = {}
    for name in ("oil", "gas", "water", "casing_pressure", "tubing_pressure", "pump_inlet_pressure"):
        column = getattr(columns, name)
        if column:
            values = [_parse_float(row.get(column)) for row in rows]
            profile = _signal_profile(values, len(rows))
            profile["trend"] = _trend(values)
            profile["column"] = column
            signals[name] = profile

    production_signals = {key: value for key, value in signals.items() if key in {"oil", "gas", "water"}}
    pressure_signals = {
        key: value
        for key, value in signals.items()
        if key in {"casing_pressure", "tubing_pressure", "pump_inlet_pressure"}
    }
    usable_pressure = [name for name, profile in pressure_signals.items() if profile["isUsable"]]
    usable_production = [name for name, profile in production_signals.items() if profile["isUsable"]]
    origin_candidates = _origin_candidates(dates, rows, columns)
    pressure_diagnostics = _pressure_projection_diagnostics(rows, columns)

    return {
        "well": well,
        "rowCount": len(rows),
        "dateStart": dates[0].isoformat() if dates else None,
        "dateEnd": dates[-1].isoformat() if dates else None,
        "cadence": _cadence(dates),
        "productionSignals": production_signals,
        "pressureSignals": pressure_signals,
        "usableProduction": usable_production,
        "usablePressure": usable_pressure,
        "fitOriginCandidates": origin_candidates,
        "pressureProjectionDiagnostics": pressure_diagnostics,
    }


def _recommend_for_profile(profile: dict[str, Any]) -> dict[str, Any]:
    row_count = profile["rowCount"]
    cadence = profile["cadence"]["cadence"]
    has_pressure = bool(profile["usablePressure"])
    usable_prod = profile["usableProduction"]

    eligible: list[dict[str, Any]] = []
    not_eligible: list[dict[str, Any]] = []
    reasons: list[str] = []

    if not usable_prod:
        return {
            "well": profile["well"],
            "qc": "red",
            "recommendedMethod": None,
            "eligibleMethods": [],
            "notEligibleMethods": [{"method": "all", "reason": "No usable production phase with at least 50% coverage and 6 positive points."}],
            "reasons": ["No usable production phase was detected."],
        }

    if row_count >= 12:
        eligible.append({"method": "arps_hyperbolic_to_exponential", "reason": "Enough production history for constrained decline fitting."})
        eligible.append({"method": "arps_hyperbolic", "reason": "Enough production history for hyperbolic candidate fitting."})
    else:
        not_eligible.append({"method": "arps_hyperbolic_to_exponential", "reason": "Fewer than 12 valid dated rows."})

    if row_count >= 6:
        eligible.append({"method": "arps_exponential", "reason": "Enough points for a simple decline fallback."})

    if cadence == "daily" and row_count >= 60 and has_pressure:
        eligible.append({"method": "pressure_aware_hybrid_residual", "reason": "Daily production and usable pressure support residual diagnostics."})
    else:
        not_eligible.append({
            "method": "pressure_aware_hybrid_residual",
            "reason": "Requires daily history, at least 60 rows, and usable pressure coverage.",
        })

    if cadence == "monthly" and row_count >= 12:
        eligible.append({"method": "monthly_simple_decline", "reason": "Monthly cadence favors stable reserves-style fitting."})
    else:
        not_eligible.append({"method": "monthly_simple_decline", "reason": "Requires monthly cadence and at least 12 rows."})

    if cadence == "daily" and row_count >= 90:
        eligible.append({"method": "change_point_fit_window_scan", "reason": "Daily history is long enough to test alternate fit windows."})

    recommended = "arps_hyperbolic_to_exponential"
    qc = "green"
    if has_pressure and cadence == "daily" and row_count >= 60:
        recommended = "pressure_aware_review_then_arps_hyp_to_exp"
        reasons.append("Use pressure to classify operational effects before accepting the decline fit.")
    elif cadence == "monthly":
        recommended = "monthly_simple_decline_then_arps_hyp_to_exp"
        reasons.append("Monthly data should avoid over-detailed daily residual models.")
    elif row_count < 12:
        recommended = "arps_exponential"
        qc = "yellow"
        reasons.append("Short history limits method confidence.")

    if not has_pressure:
        reasons.append("No usable pressure signal; pressure-aware hybrid methods should not run.")
    if cadence in {"unknown", "sparse"}:
        qc = "yellow"
        reasons.append("Cadence is sparse or unknown; human review is recommended.")
    if any(candidate["type"] == "sustained_rate_uplift" for candidate in profile.get("fitOriginCandidates", [])):
        qc = "yellow"
        reasons.append("Possible recompletion/stimulation or operating changes detected; test fit origins across candidate regime changes.")

    diagnostics = profile.get("pressureProjectionDiagnostics", [])
    interpretations = {item["interpretation"] for item in diagnostics}
    if "possible_constraint_or_operational_issue" in interpretations:
        qc = "yellow"
        reasons.append("Pressure/rate pattern suggests possible constraint or operating issue; avoid projecting recent rate loss as pure depletion.")
    if "drawdown_or_recompletion_response" in interpretations:
        qc = "yellow"
        reasons.append("Pressure/rate pattern suggests drawdown change or recompletion response; test post-event forecast origins.")
    if "hidden_depletion_risk" in interpretations:
        qc = "yellow"
        reasons.append("Pressure is falling while rate is flat; projection carries hidden depletion risk.")
    if "operationally_unstable" in interpretations:
        qc = "yellow"
        reasons.append("Rate and pressure volatility suggest unstable operations; human review is recommended.")

    reasons.append("Recommendation is limited-data forecasting guidance, not a full reservoir-engineering calculation.")

    return {
        "well": profile["well"],
        "qc": qc,
        "recommendedMethod": recommended,
        "eligibleMethods": eligible,
        "notEligibleMethods": not_eligible,
        "reasons": reasons,
    }


@mcp.tool()
def profile_csv(csv_path: str, limit_wells: int | None = None) -> dict[str, Any]:
    """Profile production and pressure signal availability for each well in a CSV file."""
    columns, by_well = _load_csv(csv_path)
    well_names = sorted(by_well)
    if limit_wells:
        well_names = well_names[: max(0, limit_wells)]
    profiles = [_profile_well(well, by_well[well], columns) for well in well_names]
    return {
        "csvPath": str(Path(csv_path).expanduser().resolve()),
        "wellCount": len(by_well),
        "profiledWellCount": len(profiles),
        "columnMap": columns.__dict__,
        "profiles": profiles,
    }


@mcp.tool()
def recommend_methods(profile: dict[str, Any]) -> dict[str, Any]:
    """Recommend eligible forecast method families for one well profile from profile_csv."""
    return _recommend_for_profile(profile)


@mcp.tool()
def convert_decline_convention(
    nominal_di: float,
    b_factor: float,
    terminal_dmin: float,
    input_time_unit: str = "day",
    as_percent: bool = True,
) -> dict[str, Any]:
    """Convert internal nominal decline parameters to commercial app entry conventions.

    Internal fitters often solve Arps parameters in nominal decline per model time unit.
    ARIES, ComboCurve, PHDWin, Mosaic, and similar tools commonly expect:
    - initial decline as effective secant annual decline
    - terminal decline as effective annual exponential decline

    Set input_time_unit to the unit used by the fitter time axis: day, month, or year.
    """
    nominal_di_annual = _nominal_to_annual(float(nominal_di), input_time_unit)
    terminal_dmin_annual = _nominal_to_annual(float(terminal_dmin), input_time_unit)
    effective_initial = _effective_secant_initial(nominal_di_annual, float(b_factor))
    effective_terminal = _effective_exponential_annual(terminal_dmin_annual)
    scale = 100.0 if as_percent else 1.0
    unit_label = "percent" if as_percent else "fraction"
    return {
        "input": {
            "nominalDi": nominal_di,
            "bFactor": b_factor,
            "terminalDmin": terminal_dmin,
            "inputTimeUnit": input_time_unit,
        },
        "pinnedTimeUnit": "year",
        "nominalDiAnnual": nominal_di_annual,
        "terminalDminNominalAnnual": terminal_dmin_annual,
        "initialDeclineEffectiveSecantAnnual": effective_initial * scale,
        "terminalDeclineEffectiveAnnualExponential": effective_terminal * scale,
        "declineUnit": unit_label,
        "entryValues": {
            "initialDecline": round(effective_initial * scale, 6),
            "bFactor": b_factor,
            "terminalDecline": round(effective_terminal * scale, 6),
        },
        "notes": [
            "Use initialDecline as the commercial app forecast-entry initial decline.",
            "Use terminalDecline as the effective annual exponential terminal decline.",
            "Do not export nominal Di directly into apps expecting effective annual decline.",
        ],
    }


@mcp.tool()
def profile_and_recommend(csv_path: str, limit_wells: int | None = None) -> dict[str, Any]:
    """Profile a CSV and recommend forecast method families for each well."""
    profiled = profile_csv(csv_path, limit_wells=limit_wells)
    recommendations = [_recommend_for_profile(profile) for profile in profiled["profiles"]]
    qc_counts: dict[str, int] = defaultdict(int)
    for item in recommendations:
        qc_counts[item["qc"]] += 1
    return {
        **profiled,
        "recommendations": recommendations,
        "qcCounts": dict(sorted(qc_counts.items())),
    }


if __name__ == "__main__":
    mcp.run()
