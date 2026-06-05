#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import math
import shutil
import zipfile
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from forecasting_mcp import profile_and_recommend


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "data" / "input"
OUTPUT_DIR = ROOT / "data" / "output" / "monthly_production_dca_batch"
CHART_DIR = OUTPUT_DIR / "primary_product_charts"

DEFAULT_PRODUCTION_ZIP = INPUT_DIR / "env_csv-Production-badec_2026-06-04.zip"
DEFAULT_WELLS_ZIP = INPUT_DIR / "env_csv-Wells-e8117_2026-06-04.zip"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "output" / "enverus_2026-06-04_all_wells_monthly"
DEFAULT_CHART_CONFIG = ROOT / "chart_config.default.json"

PRIMARY_FCAST_YEARS = 30.0
FCAST_STEP_YEARS = 1.0 / 12.0
TERMINAL_NOMINAL_D = 0.06

DEFAULT_BATCH_CONFIG: dict[str, Any] = {
    "plot": {
        "width": 1120,
        "height": 700,
        "printMarginPx": 30,
        "left": 72,
        "top": 116,
        "right": 920,
        "bottom": 438,
        "clipForecastBelowAxis": True,
    },
    "forecast": {
        "years": 30.0,
        "stepYears": 1.0 / 12.0,
        "terminalEffectiveAnnualDecline": 0.08,
        "terminalNominalDeclineAnnual": 0.06,
        "yellowTailWapeThreshold": 0.30,
        "redTailWapeThreshold": 0.60,
        "yellowIfTailR2Below": 0.0,
        "recentOutlierLowRatio": 0.2,
        "preferPeakHyperbolic": True,
        "peakHyperbolicMinPositiveMonths": 36,
        "peakHyperbolicMaxTailWapePenalty": 0.025,
        "peakHyperbolicMaxTailWapeRatio": 1.75,
        "peakHyperbolicMaxPeakMonthIndex": 6,
        "peakHyperbolicMinPeakToCurrentRatio": 3.0,
        "peakHyperbolicMinPrimaryForecastVolumeRatio": 1.0,
        "lifeLimitRates": {"Oil": 1.0, "Gas": 10.0},
    },
    "lifecycle": {
        "earlyStagePositivePrimaryMonths": 6,
    },
    "series": {
        "oil": {"color": "#288246", "label": "Oil"},
        "gas": {"color": "#be4137", "label": "Gas"},
        "water": {"color": "#2d69b4", "label": "Water"},
    },
    "ratios": {
        "enabled": True,
        "rightAxisMinDefault": 0.1,
        "matchLeftAxisCycles": True,
        "colors": {"GOR": "#dc379b", "WOR_WGR": "#00918c"},
    },
    "pressure": {
        "enabledWhenAvailable": True,
        "axis": "right",
        "notes": [
            "Pressure is not present in the current monthly upload.",
            "When usable pressure exists, show pressure context only; do not use it as a standalone physics forecast.",
            "Synthetic diagnostic contexts: no_pressure_diagnostic, depletion_supported, possible_constraint_or_operational_issue, drawdown_or_recompletion_response, hidden_depletion_risk, operationally_unstable.",
        ],
        "series": {
            "casingPressure": {"color": "#9a6a24", "label": "Casing P"},
            "tubingPressure": {"color": "#7d62b4", "label": "Tubing P"},
            "pumpInletPressure": {"color": "#607d80", "label": "Pump Intake P"},
        },
    },
    "qcColors": {"Green": "#208a4a", "Yellow": "#b98414", "Red": "#b92d2d"},
    "legend": {"x": 982, "lineLength": 22, "fontSize": 10},
}

CHART_CONFIG: dict[str, Any] = DEFAULT_BATCH_CONFIG


def parse_float(value: Any) -> float | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m", "%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_chart_config(path: Path | None) -> dict[str, Any]:
    config = DEFAULT_BATCH_CONFIG
    if path and path.exists():
        with path.open("r", encoding="utf-8") as handle:
            config = deep_merge(config, json.load(handle))
    return config


def hex_to_rgb(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return tuple(int(v) for v in value)  # type: ignore[return-value]
    text = str(value or "").strip()
    if text.startswith("#") and len(text) == 7:
        try:
            return int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16)
        except ValueError:
            return fallback
    return fallback


def read_single_csv_zip(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected exactly one CSV in {path}, found {csv_names}")
        data = archive.read(csv_names[0]).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(data)))


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT = load_font(15)
FONT_SMALL = load_font(12)
FONT_TINY = load_font(10)
FONT_LEGEND = load_font(10)
FONT_BOLD = load_font(18, True)
FONT_TITLE = load_font(25, True)

RATIO_COLORS = {
    "GOR": (220, 55, 155),
    "WOR_WGR": (0, 145, 140),
}
PRESSURE_COLORS = {
    "CasingPressure": (145, 90, 40),
    "TubingPressure": (110, 85, 170),
    "PumpInletPressure": (80, 120, 120),
}


def clean_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in value).strip().replace(" ", "_")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def normalize_inputs(production_zip: Path, wells_zip: Path, output_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prod_rows = read_single_csv_zip(production_zip)
    well_rows = read_single_csv_zip(wells_zip)

    metadata: dict[str, dict[str, Any]] = {}
    for row in well_rows:
        name = (row.get("WellName") or "").strip()
        if not name:
            continue
        metadata[name] = {
            "API_UWI": row.get("API_UWI", ""),
            "WellID": row.get("WellID", ""),
            "Operator": row.get("ENVOperator") or row.get("RawOperator") or row.get("ProducingOperator") or "",
            "County": row.get("County", ""),
            "Formation": row.get("Formation", ""),
            "ENVInterval": row.get("ENVInterval", ""),
            "ENVPlay": row.get("ENVPlay", ""),
            "ENVSubPlay": row.get("ENVSubPlay", ""),
            "Latitude": parse_float(row.get("Latitude")),
            "Longitude": parse_float(row.get("Longitude")),
            "Latitude_BH": parse_float(row.get("Latitude_BH")),
            "Longitude_BH": parse_float(row.get("Longitude_BH")),
            "LateralLength_FT": parse_float(row.get("LateralLength_FT")) or parse_float(row.get("ENVEffectiveLateralLength")),
            "FirstProdDate": row.get("FirstProdDate") or row.get("FirstProdMonth") or "",
        }

    by_well: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized_rows: list[dict[str, Any]] = []
    for row in prod_rows:
        well = (row.get("WellName") or "").strip()
        dt = parse_date(row.get("ProducingMonth"))
        days = parse_float(row.get("ProducingDays"))
        if not well or not dt or not days or days <= 0:
            continue
        oil = parse_float(row.get("LiquidsProd_BBL")) or 0.0
        gas = parse_float(row.get("GasProd_MCF")) or 0.0
        water = parse_float(row.get("WaterProd_BBL")) or 0.0
        item = {
            "well": well,
            "date": dt,
            "date_iso": dt.strftime("%Y-%m-%d"),
            "producing_days": days,
            "oil_bbl": oil,
            "gas_mcf": gas,
            "water_bbl": water,
            "oil_bopd": oil / days,
            "gas_mcfd": gas / days,
            "water_bwpd": water / days,
        }
        by_well[well].append(item)
        normalized_rows.append(item)

    for well in by_well:
        by_well[well].sort(key=lambda item: item["date"])

    with (output_dir / "normalized_production.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "WellName",
            "Date",
            "ProducingDays",
            "Oil_BBL",
            "Gas_MCF",
            "Water_BBL",
            "Oil_BOPD",
            "Gas_MCFD",
            "Water_BWPD",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(normalized_rows, key=lambda item: (item["well"], item["date"])):
            writer.writerow(
                {
                    "WellName": row["well"],
                    "Date": row["date_iso"],
                    "ProducingDays": row["producing_days"],
                    "Oil_BBL": round(row["oil_bbl"], 6),
                    "Gas_MCF": round(row["gas_mcf"], 6),
                    "Water_BBL": round(row["water_bbl"], 6),
                    "Oil_BOPD": round(row["oil_bopd"], 6),
                    "Gas_MCFD": round(row["gas_mcfd"], 6),
                    "Water_BWPD": round(row["water_bwpd"], 6),
                }
            )

    with (output_dir / "well_metadata_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "WellName",
            "API_UWI",
            "WellID",
            "Operator",
            "County",
            "Formation",
            "ENVInterval",
            "ENVPlay",
            "ENVSubPlay",
            "Latitude",
            "Longitude",
            "Latitude_BH",
            "Longitude_BH",
            "LateralLength_FT",
            "FirstProdDate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for well in sorted(by_well):
            row = {"WellName": well}
            row.update(metadata.get(well, {}))
            writer.writerow(row)

    manifest = {
        "source": "tauris-skills forecasting-mcp",
        "productionZip": display_path(production_zip),
        "wellsZip": display_path(wells_zip),
        "wellCount": len(by_well),
        "productionRows": len(normalized_rows),
        "normalization": "Monthly volumes divided by reported ProducingDays to average daily rates.",
        "pressureDataAvailable": False,
    }
    (output_dir / "input_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dict(by_well), metadata


def elapsed_years(rows: list[dict[str, Any]]) -> list[float]:
    start = rows[0]["date"]
    return [(row["date"] - start).days / 365.25 for row in rows]


def wape(actual: list[float], pred: list[float]) -> float | None:
    denom = sum(abs(v) for v in actual)
    if denom <= 0 or len(actual) != len(pred):
        return None
    return sum(abs(a - p) for a, p in zip(actual, pred)) / denom


def rmse(actual: list[float], pred: list[float]) -> float | None:
    if not actual or len(actual) != len(pred):
        return None
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, pred)) / len(actual))


def r_squared(actual: list[float], pred: list[float]) -> float | None:
    if len(actual) < 2 or len(actual) != len(pred):
        return None
    mean_actual = sum(actual) / len(actual)
    total = sum((a - mean_actual) ** 2 for a in actual)
    if total <= 0:
        return None
    residual = sum((a - p) ** 2 for a, p in zip(actual, pred))
    return 1.0 - residual / total


def fmt_metric(value: Any, digits: int = 2) -> str:
    if value is None or value == "":
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_log_tick(value: float) -> str:
    if value >= 1000:
        return f"{value:,.0f}"
    if value >= 1:
        return f"{value:g}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def compact_method(value: str) -> str:
    text = str(value or "n/a")
    text = text.replace("monthly DCA ", "")
    text = text.replace("no DCA fit generated", "no DCA fit")
    text = text.replace("2-stage trend-to-flat", "2-stage")
    text = text.replace("1-stage flat", "flat")
    return text


def ratio_bounds(numerator_future: tuple[list[float], list[float]] | None, denominator_future: tuple[list[float], list[float]] | None) -> tuple[float | None, float | None]:
    if not numerator_future or not denominator_future:
        return None, None
    values = [n / d for n, d in zip(numerator_future[1], denominator_future[1]) if n > 0 and d > 0]
    if not values:
        return None, None
    return values[0], values[-1]


def terminal_nominal_decline() -> float:
    effective = parse_float(CHART_CONFIG.get("forecast", {}).get("terminalEffectiveAnnualDecline"))
    if effective is not None and 0.0 < effective < 1.0:
        return -math.log(1.0 - effective)
    configured = parse_float(CHART_CONFIG.get("forecast", {}).get("terminalNominalDeclineAnnual"))
    return configured if configured is not None and configured > 0 else TERMINAL_NOMINAL_D


def terminal_effective_decline() -> float:
    return 1.0 - math.exp(-terminal_nominal_decline())


def arps_rate(qi: float, di: float, b: float, t: float) -> float:
    if qi <= 0:
        return 0.0
    if b <= 1e-9:
        return qi * math.exp(-di * t)
    terminal_d = terminal_nominal_decline()
    switch_t = max(0.0, (di / terminal_d - 1.0) / (b * di)) if di > terminal_d else 0.0
    if t <= switch_t:
        return qi / ((1.0 + b * di * t) ** (1.0 / b))
    q_switch = qi / ((1.0 + b * di * switch_t) ** (1.0 / b))
    return q_switch * math.exp(-terminal_d * (t - switch_t))


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    denom = sum((x - xbar) ** 2 for x in xs)
    if denom <= 0:
        return None
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / denom
    intercept = ybar - slope * xbar
    return intercept, slope


def fit_arps_candidate(times: list[float], rates: list[float], start_index: int, b: float, label: str) -> dict[str, Any] | None:
    points = [(times[i] - times[start_index], rates[i]) for i in range(start_index, len(rates)) if rates[i] > 0]
    if len(points) < 6:
        return None
    xs = [p[0] for p in points]
    qs = [p[1] for p in points]
    if b <= 1e-9:
        fit = linear_fit(xs, [math.log(q) for q in qs])
        if not fit:
            return None
        intercept, slope = fit
        qi = math.exp(intercept)
        di = max(0.001, min(5.0, -slope))
    else:
        fit = linear_fit(xs, [q ** (-b) for q in qs])
        if not fit:
            return None
        intercept, slope = fit
        if intercept <= 0 or slope <= 0:
            return None
        qi = intercept ** (-1.0 / b)
        di = max(0.001, min(5.0, slope / (b * intercept)))

    hist_pred = [arps_rate(qi, di, b, max(0.0, t - times[start_index])) for t in times]
    tail_idx = [i for i in range(start_index, len(rates)) if rates[i] > 0][-12:]
    if len(tail_idx) < 3:
        return None
    tail_actual = [rates[i] for i in tail_idx]
    tail_pred = [hist_pred[i] for i in tail_idx]
    fit_idx = [i for i in range(start_index, len(rates)) if rates[i] > 0]
    fit_actual = [rates[i] for i in fit_idx]
    fit_pred = [hist_pred[i] for i in fit_idx]
    tail_wape = wape(tail_actual, tail_pred)
    all_wape = wape(fit_actual, fit_pred)
    return {
        "method": label,
        "qi": qi,
        "di_nominal_annual": di,
        "annual_di_effective": 1.0 - math.exp(-di),
        "b": b,
        "origin_index": start_index,
        "origin_year": times[start_index],
        "tail_start_index": tail_idx[0],
        "tail_end_index": tail_idx[-1],
        "tail_start_year": times[tail_idx[0]],
        "tail_end_year": times[tail_idx[-1]],
        "tail_wape": tail_wape,
        "tail_rmse": rmse(tail_actual, tail_pred),
        "tail_r2": r_squared(tail_actual, tail_pred),
        "fit_wape": all_wape,
        "fit_rmse": rmse(fit_actual, fit_pred),
        "fit_r2": r_squared(fit_actual, fit_pred),
    }


def choose_fit(times: list[float], rates: list[float]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    positive = [i for i, q in enumerate(rates) if q > 0]
    if len(positive) < 6:
        return None, []
    peak_index = max(positive, key=lambda i: rates[i])
    starts = {positive[0], positive[max(0, len(positive) - 24)], positive[max(0, len(positive) - 36)], peak_index}
    candidates: list[dict[str, Any]] = []
    for start in sorted(starts):
        for b in (0.0, 0.5, 1.0, 1.5):
            label = f"monthly DCA Arps b={b:g}, origin={start + 1}"
            candidate = fit_arps_candidate(times, rates, start, b, label)
            if candidate:
                candidates.append(candidate)
    if not candidates:
        return None, []
    candidates.sort(key=lambda item: (item["tail_wape"] if item["tail_wape"] is not None else 999.0, item["origin_index"]))
    recent_best = candidates[0]
    recent_best["selection_basis"] = "best recent tail error"
    recent_best["alternate_recent_method"] = ""
    recent_best["alternate_recent_tail_wape"] = None

    forecast_config = CHART_CONFIG.get("forecast", {})
    if not forecast_config.get("preferPeakHyperbolic", True):
        return recent_best, candidates

    min_months = int(forecast_config.get("peakHyperbolicMinPositiveMonths", 36))
    max_peak_index = int(forecast_config.get("peakHyperbolicMaxPeakMonthIndex", 6)) - 1
    min_peak_to_current = float(forecast_config.get("peakHyperbolicMinPeakToCurrentRatio", 3.0))
    max_wape_penalty = float(forecast_config.get("peakHyperbolicMaxTailWapePenalty", 0.025))
    max_wape_ratio = float(forecast_config.get("peakHyperbolicMaxTailWapeRatio", 1.75))
    min_volume_ratio = float(forecast_config.get("peakHyperbolicMinPrimaryForecastVolumeRatio", 1.0))

    if len(positive) < min_months or peak_index > max_peak_index:
        return recent_best, candidates

    current_positive_rate = rates[positive[-1]]
    if current_positive_rate <= 0 or rates[peak_index] / current_positive_rate < min_peak_to_current:
        return recent_best, candidates

    recent_wape = recent_best.get("tail_wape")
    if recent_wape is None:
        return recent_best, candidates

    peak_hyperbolic = [
        candidate
        for candidate in candidates
        if candidate["origin_index"] == peak_index and candidate["b"] > 0 and candidate.get("tail_wape") is not None
    ]
    if not peak_hyperbolic:
        return recent_best, candidates

    peak_best = sorted(peak_hyperbolic, key=lambda item: (item["tail_wape"], item["b"]))[0]
    peak_wape = peak_best["tail_wape"]
    if peak_wape <= recent_wape + max_wape_penalty or peak_wape <= recent_wape * max_wape_ratio:
        recent_volume = candidate_forecast_volume(recent_best, times)
        peak_volume = candidate_forecast_volume(peak_best, times)
        if recent_volume > 0 and peak_volume < recent_volume * min_volume_ratio:
            return recent_best, candidates
        peak_best["selection_basis"] = "guarded peak-origin hyperbolic preference"
        peak_best["alternate_recent_method"] = recent_best["method"]
        peak_best["alternate_recent_tail_wape"] = recent_wape
        peak_best["alternate_recent_forecast_volume"] = recent_volume
        peak_best["forecast_volume_delta_vs_recent"] = peak_volume - recent_volume
        return peak_best, candidates

    return recent_best, candidates


def smooth_ratio_model(times: list[float], numerator: list[float], denominator: list[float], ratio_name: str) -> dict[str, Any]:
    points = [(t, n / d) for t, n, d in zip(times, numerator, denominator) if n > 0 and d > 0]
    if len(points) < 4:
        return {
            "method": f"insufficient {ratio_name}",
            "tail_wape": None,
            "tail_rmse": None,
            "tail_r2": None,
            "points": len(points),
            "predict": lambda _t: 0.0,
        }
    ratios = [p[1] for p in points]
    med = median(ratios)
    filtered = [(t, r) for t, r in points if med <= 0 or 0.05 * med <= r <= 20.0 * med]
    if len(filtered) >= 4:
        points = filtered
    tail_n = min(12, max(3, len(points) // 4))
    train = points[:-tail_n] if len(points) > tail_n + 3 else points
    tail = points[-tail_n:]
    flat_value = median([r for _, r in train[-12:]])
    flat_pred = [flat_value for _ in tail]
    tail_actual = [r for _, r in tail]
    flat_wape = wape(tail_actual, flat_pred)
    flat_rmse = rmse(tail_actual, flat_pred)
    flat_r2 = r_squared(tail_actual, flat_pred)

    trend_predict = None
    trend_wape = None
    trend_rmse = None
    trend_r2 = None
    trend_points = train[-min(24, len(train)) :]
    fit = linear_fit([t for t, _ in trend_points], [math.log(max(r, 1e-9)) for _, r in trend_points])
    if fit:
        intercept, slope = fit
        lo = min(r for _, r in trend_points) * 0.35
        hi = max(r for _, r in trend_points) * 1.75
        t_flat = max(t for t, _ in points) + 5.0

        def _trend(t: float) -> float:
            use_t = min(t, t_flat)
            return max(lo, min(hi, math.exp(intercept + slope * use_t)))

        trend_predict = _trend
        trend_pred = [_trend(t) for t, _ in tail]
        trend_wape = wape(tail_actual, trend_pred)
        trend_rmse = rmse(tail_actual, trend_pred)
        trend_r2 = r_squared(tail_actual, trend_pred)

    use_trend = trend_predict and trend_wape is not None and (flat_wape is None or trend_wape < flat_wape * 0.98)
    if use_trend:
        return {
            "method": f"2-stage trend-to-flat {ratio_name}",
            "tail_wape": trend_wape,
            "tail_rmse": trend_rmse,
            "tail_r2": trend_r2,
            "points": len(points),
            "predict": trend_predict,
        }
    return {
        "method": f"1-stage flat {ratio_name}",
        "tail_wape": flat_wape,
        "tail_rmse": flat_rmse,
        "tail_r2": flat_r2,
        "points": len(points),
        "predict": lambda _t: flat_value,
    }


def forecast_series(best: dict[str, Any], times: list[float]) -> tuple[list[float], list[float]]:
    start = times[best["origin_index"]]
    final_t = max(times[-1], start) + float(CHART_CONFIG["forecast"].get("years", PRIMARY_FCAST_YEARS))
    future_times: list[float] = []
    step_years = float(CHART_CONFIG["forecast"].get("stepYears", FCAST_STEP_YEARS))
    t = times[-1] + step_years
    while t <= final_t + 1e-9:
        future_times.append(t)
        t += step_years
    future_rates = [arps_rate(best["qi"], best["di_nominal_annual"], best["b"], max(0.0, t - start)) for t in future_times]
    return trim_forecast_tail(future_times, future_rates)


def trim_forecast_tail(times: list[float], rates: list[float], min_positive_rate: float = 1e-6) -> tuple[list[float], list[float]]:
    """Drop trailing zero/non-positive forecast points so plots stop at the final valid forecast rate."""
    last = -1
    for index, rate in enumerate(rates):
        if rate is not None and rate > min_positive_rate:
            last = index
    if last < 0:
        return [], []
    return times[: last + 1], rates[: last + 1]


def remaining_volume(rate_series: list[float]) -> float:
    step_years = float(CHART_CONFIG["forecast"].get("stepYears", FCAST_STEP_YEARS))
    return sum(q * 365.25 * step_years for q in rate_series)


def total_life_years(times: list[float], *futures: tuple[list[float], list[float]] | None) -> float:
    endpoints = [times[-1]] if times else [0.0]
    for future in futures:
        if future and future[0] and future[1]:
            endpoints.append(future[0][-1])
    return max(endpoints)


def primary_life_years(times: list[float], primary: str, primary_future: tuple[list[float], list[float]] | None) -> float:
    if not times:
        return 0.0
    life_limit_rates = CHART_CONFIG.get("forecast", {}).get("lifeLimitRates", {})
    if isinstance(life_limit_rates, dict):
        limit = parse_float(life_limit_rates.get(primary))
    else:
        limit = None
    if limit is None or limit <= 0:
        limit = 1.0 if primary == "Oil" else 10.0
    if not primary_future or not primary_future[0] or not primary_future[1]:
        return times[-1]
    for t, q in zip(primary_future[0], primary_future[1]):
        if q < limit:
            return t
    return primary_future[0][-1]


def primary_life_limit_label(primary: str) -> str:
    life_limit_rates = CHART_CONFIG.get("forecast", {}).get("lifeLimitRates", {})
    if isinstance(life_limit_rates, dict):
        limit = parse_float(life_limit_rates.get(primary))
    else:
        limit = None
    if limit is None or limit <= 0:
        limit = 1.0 if primary == "Oil" else 10.0
    unit = "BOPD" if primary == "Oil" else "MCFD"
    return f"{limit:g} {unit}"


def candidate_forecast_volume(candidate: dict[str, Any], times: list[float]) -> float:
    return remaining_volume(forecast_series(candidate, times)[1])


def classify_lifecycle(primary_positive_months: int, best: dict[str, Any] | None) -> tuple[str, str, str]:
    if primary_positive_months <= 0:
        return (
            "No primary production",
            "No positive primary-product production points.",
            "Cannot forecast until primary production exists.",
        )
    early_months = int(CHART_CONFIG["lifecycle"].get("earlyStagePositivePrimaryMonths", 6))
    if primary_positive_months < early_months:
        return (
            "Still early stage",
            f"Fewer than {early_months} positive primary-product months; DCA shape is not established.",
            "Candidate for future type curve or nearby-offset proxy.",
        )
    if not best:
        return (
            "Insufficient stable DCA shape",
            "Enough positive months exist, but no stable DCA candidate passed fit requirements.",
            "Candidate for future type curve or nearby-offset proxy.",
        )
    return (
        "DCA-ready",
        "Enough positive primary-product months for a local monthly DCA fit.",
        "Not needed for current DCA run.",
    )


def recent_fit_warning(best: dict[str, Any] | None, rates: list[float]) -> str:
    if not best:
        return ""
    warnings: list[str] = []
    tail_wape = best.get("tail_wape")
    tail_r2 = best.get("tail_r2")
    yellow_wape = float(CHART_CONFIG["forecast"].get("yellowTailWapeThreshold", 0.30))
    yellow_r2 = float(CHART_CONFIG["forecast"].get("yellowIfTailR2Below", 0.0))
    if tail_wape is not None and tail_wape > yellow_wape:
        warnings.append(f"recent fit error > {yellow_wape * 100:.0f}%")
    if tail_r2 is not None and tail_r2 < yellow_r2:
        warnings.append(f"recent R2 < {yellow_r2:g}")
    start = best.get("tail_start_index")
    end = best.get("tail_end_index")
    if start is not None and end is not None:
        tail_rates = [rate for rate in rates[int(start) : int(end) + 1] if rate > 0]
        if len(tail_rates) >= 3:
            tail_median = median(tail_rates)
            low_ratio = float(CHART_CONFIG["forecast"].get("recentOutlierLowRatio", 0.2))
            if tail_median > 0 and min(tail_rates) < tail_median * low_ratio:
                warnings.append("possible low-rate operational outlier in recent window")
    return "; ".join(warnings)


def text_key(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def reservoir_key(meta: dict[str, Any]) -> str:
    return text_key(meta.get("Formation")) or text_key(meta.get("ENVInterval")) or text_key(meta.get("ENVSubPlay"))


def well_lat_lon(meta: dict[str, Any]) -> tuple[float | None, float | None]:
    lat = meta.get("Latitude_BH") or meta.get("Latitude")
    lon = meta.get("Longitude_BH") or meta.get("Longitude")
    return lat, lon


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.7613
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * radius_miles * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def build_analog_screen(summary_rows: list[dict[str, Any]], metadata: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_well = {row["WellName"]: row for row in summary_rows}
    dca_ready = [
        row
        for row in summary_rows
        if row.get("LifecycleStage") == "DCA-ready" and row.get("PrimaryMethodUsed") != "no DCA fit generated"
    ]
    analog_rows: list[dict[str, Any]] = []
    for target in summary_rows:
        if target.get("LifecycleStage") == "DCA-ready":
            target["AnalogCandidateCount"] = 0
            target["TopAnalogWells"] = ""
            continue
        target_meta = metadata.get(target["WellName"], {})
        target_reservoir = reservoir_key(target_meta)
        target_lat, target_lon = well_lat_lon(target_meta)
        target_lateral = parse_float(target.get("LateralLength_FT"))
        if not target_reservoir or target_lat is None or target_lon is None or not target_lateral:
            target["AnalogCandidateCount"] = 0
            target["TopAnalogWells"] = ""
            target["TypeCurveProxyStatus"] = "Needs type curve/offset proxy; missing reservoir, location, or lateral metadata."
            continue

        candidates: list[dict[str, Any]] = []
        for candidate in dca_ready:
            if candidate["WellName"] == target["WellName"] or candidate.get("PrimaryProduct") != target.get("PrimaryProduct"):
                continue
            candidate_meta = metadata.get(candidate["WellName"], {})
            if reservoir_key(candidate_meta) != target_reservoir:
                continue
            candidate_lat, candidate_lon = well_lat_lon(candidate_meta)
            candidate_lateral = parse_float(candidate.get("LateralLength_FT"))
            if candidate_lat is None or candidate_lon is None or not candidate_lateral:
                continue
            distance = haversine_miles(target_lat, target_lon, candidate_lat, candidate_lon)
            lateral_ratio = candidate_lateral / target_lateral if target_lateral else 0.0
            if distance > 25.0 or not 0.65 <= lateral_ratio <= 1.35:
                continue
            score = distance + abs(math.log(max(lateral_ratio, 1e-9))) * 10.0
            candidates.append(
                {
                    "TargetWellName": target["WellName"],
                    "AnalogWellName": candidate["WellName"],
                    "PrimaryProduct": target.get("PrimaryProduct"),
                    "ReservoirKey": target_reservoir,
                    "DistanceMiles": round(distance, 3),
                    "TargetLateralLength_FT": target_lateral,
                    "AnalogLateralLength_FT": candidate_lateral,
                    "LateralRatio": round(lateral_ratio, 4),
                    "AnalogQC": candidate.get("QC"),
                    "AnalogMethod": candidate.get("PrimaryMethodUsed"),
                    "AnalogTailWAPEPercent": candidate.get("PrimaryTailWAPEPercent"),
                    "AnalogEUR_MBOEPerFT": candidate.get("EUR_MBOEPerFT"),
                    "AnalogScore": round(score, 4),
                }
            )
        candidates.sort(key=lambda item: item["AnalogScore"])
        selected = candidates[:5]
        analog_rows.extend(selected)
        target["AnalogCandidateCount"] = len(selected)
        target["TopAnalogWells"] = " | ".join(item["AnalogWellName"] for item in selected[:3])
        if selected:
            target["TypeCurveProxyStatus"] = "Potential type-curve proxy candidates found; not applied in this run."
        else:
            target["TypeCurveProxyStatus"] = "Needs type curve/offset proxy; no strict nearby same-reservoir analog found."

    for row in summary_rows:
        row.setdefault("AnalogCandidateCount", 0)
        row.setdefault("TopAnalogWells", "")
    return analog_rows


def draw_line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int], width: int = 2, dashed: bool = False) -> None:
    if len(points) < 2:
        return
    if not dashed:
        draw.line(points, fill=color, width=width, joint="curve")
        return
    for i in range(1, len(points)):
        if i % 2 == 0:
            draw.line([points[i - 1], points[i]], fill=color, width=width)


def draw_markers(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int], radius: int = 3) -> None:
    for x, y in points:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=color)


def draw_vertical_text(img: Image.Image, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: tuple[int, int, int]) -> None:
    scratch = Image.new("RGBA", (220, 24), (255, 255, 255, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    scratch_draw.text((0, 0), text, font=font, fill=fill + (255,))
    rotated = scratch.rotate(90, expand=True)
    img.paste(rotated, xy, rotated)


def write_chart(
    well: str,
    rows: list[dict[str, Any]],
    primary: str,
    best: dict[str, Any] | None,
    oil_fit: dict[str, Any] | None,
    gas_fit: dict[str, Any] | None,
    oil_future: tuple[list[float], list[float]] | None,
    gas_future: tuple[list[float], list[float]] | None,
    water_future: tuple[list[float], list[float]] | None,
    summary: dict[str, Any],
) -> Path:
    plot_config = CHART_CONFIG["plot"]
    series_config = CHART_CONFIG["series"]
    ratio_config = CHART_CONFIG["ratios"]
    legend_config = CHART_CONFIG["legend"]
    img = Image.new("RGB", (int(plot_config["width"]), int(plot_config["height"])), "white")
    draw = ImageDraw.Draw(img)
    colors = {
        "Oil": hex_to_rgb(series_config.get("oil", {}).get("color"), (40, 130, 70)),
        "Gas": hex_to_rgb(series_config.get("gas", {}).get("color"), (190, 65, 55)),
        "Water": hex_to_rgb(series_config.get("water", {}).get("color"), (45, 105, 180)),
    }
    ratio_colors = {
        "GOR": hex_to_rgb(ratio_config.get("colors", {}).get("GOR"), RATIO_COLORS["GOR"]),
        "WOR_WGR": hex_to_rgb(ratio_config.get("colors", {}).get("WOR_WGR"), RATIO_COLORS["WOR_WGR"]),
    }
    draw.text((44, 24), well.upper(), fill=(35, 35, 35), font=FONT_TITLE)
    qc_color = hex_to_rgb(CHART_CONFIG.get("qcColors", {}).get(summary["QC"]), (80, 80, 80))
    draw.rounded_rectangle((970, 26, 1066, 58), radius=4, outline=qc_color, width=2)
    draw.text((992, 33), summary["QC"], fill=qc_color, font=FONT_BOLD)
    has_forecast = any(future and future[0] and future[1] for future in (oil_future, gas_future, water_future))
    tail_wape = f"{summary['PrimaryTailWAPEPercent']}%" if summary.get("PrimaryTailWAPEPercent") not in (None, "") else "n/a"
    line1 = f"Primary product: {primary} | Method used: {summary['PrimaryMethodUsed']} | Recent fit error: {tail_wape}"
    line2 = f"No pressure data in monthly upload | Gas: {summary['GasRatioMethod']} | Water: {summary['WaterRatioMethod']}"
    if not has_forecast:
        line2 = f"{summary.get('LifecycleStage', 'History only')} | Insufficient points for DCA shape | Type curve or nearby-offset proxy needed later"
    draw.text((46, 64), line1[:138], fill=(50, 50, 50), font=FONT)
    draw.text((46, 84), line2[:148], fill=(80, 80, 80), font=FONT_SMALL)

    plot = (int(plot_config["left"]), int(plot_config["top"]), int(plot_config["right"]), int(plot_config["bottom"]))
    left, top, right, bottom = plot
    draw.rectangle(plot, outline=(120, 120, 120), width=1)

    times = elapsed_years(rows)
    oil = [r["oil_bopd"] for r in rows]
    gas = [r["gas_mcfd"] for r in rows]
    water = [r["water_bwpd"] for r in rows]
    x_max = max([max(times), 1.0 if not has_forecast else 0.0] + (oil_future[0] if oil_future else []) + (gas_future[0] if gas_future else []) + (water_future[0] if water_future else []))
    values = [v for v in oil + gas + water if v > 0]
    for future in (oil_future, gas_future, water_future):
        if future:
            values += [v for v in future[1] if v > 0]
    selected_fit_rates: list[float] = []
    if best:
        fit_start = times[best["origin_index"]]
        selected_fit_rates = [
            arps_rate(best["qi"], best["di_nominal_annual"], best["b"], max(0.0, t - fit_start))
            if t >= fit_start
            else 0.0
            for t in times
        ]
        values += [v for v in selected_fit_rates if v > 0]
    y_min = max(0.1, 10 ** math.floor(math.log10(min(values)))) if values else 0.1
    y_max = 10 ** math.ceil(math.log10(max(values))) if values else 1000

    def sx(t: float) -> float:
        return left + (t / max(x_max, 1e-6)) * (right - left)

    def sy(q: float) -> float:
        q = max(q, y_min)
        return bottom - (math.log10(q) - math.log10(y_min)) / (math.log10(y_max) - math.log10(y_min)) * (bottom - top)

    tail_start_year = parse_float(summary.get("RecentFitStartYear"))
    tail_end_year = parse_float(summary.get("RecentFitEndYear"))
    if tail_start_year is not None and tail_end_year is not None and tail_end_year >= tail_start_year:
        band_left = max(left, min(right, sx(tail_start_year)))
        band_right = max(left, min(right, sx(tail_end_year)))
        if band_right - band_left >= 1:
            draw.rectangle((band_left, top, band_right, bottom), fill=(238, 238, 238))
            draw.text((band_left + 4, top + 6), "recent fit", fill=(100, 100, 100), font=FONT_TINY)
            draw.rectangle(plot, outline=(120, 120, 120), width=1)

    def ratio_points(numerator: list[float], denominator: list[float], point_times: list[float]) -> list[tuple[float, float]]:
        return [(t, n / d) for t, n, d in zip(point_times, numerator, denominator) if n > 0 and d > 0]

    hist_gor = ratio_points(gas, oil, times)
    if primary == "Oil":
        hist_wor_wgr = ratio_points(water, oil, times)
        ratio_label = "WOR"
    else:
        hist_wor_wgr = ratio_points(water, gas, times)
        ratio_label = "WGR"

    fcast_gor: list[tuple[float, float]] = []
    fcast_wor_wgr: list[tuple[float, float]] = []
    if oil_future and gas_future:
        fcast_gor = ratio_points(gas_future[1], oil_future[1], oil_future[0])
    if water_future:
        if primary == "Oil" and oil_future:
            fcast_wor_wgr = ratio_points(water_future[1], oil_future[1], oil_future[0])
        elif primary == "Gas" and gas_future:
            fcast_wor_wgr = ratio_points(water_future[1], gas_future[1], gas_future[0])

    ratio_values = [value for _, value in hist_gor + hist_wor_wgr + fcast_gor + fcast_wor_wgr if value > 0]
    ratio_axis: tuple[float, float] | None = None
    if ratio_values and ratio_config.get("enabled", True):
        left_cycles = max(1, int(round(math.log10(y_max) - math.log10(y_min))))
        default_ratio_min = float(ratio_config.get("rightAxisMinDefault", 0.1))
        ratio_min = default_ratio_min if min(ratio_values) >= default_ratio_min else 10 ** math.floor(math.log10(min(ratio_values)))
        ratio_max = ratio_min * (10 ** left_cycles)
        while ratio_max < max(ratio_values):
            ratio_max *= 10
        ratio_axis = (max(ratio_min, 1e-9), max(ratio_max, ratio_min * 10.0))

    def sy_ratio(value: float) -> float:
        if not ratio_axis:
            return bottom
        ratio_min, ratio_max = ratio_axis
        value = max(value, ratio_min)
        return bottom - (math.log10(value) - math.log10(ratio_min)) / (math.log10(ratio_max) - math.log10(ratio_min)) * (bottom - top)

    def visible_history_points(point_times: list[float], point_values: list[float], floor: float, mapper: Any) -> list[tuple[float, float]]:
        return [(sx(t), mapper(q)) for t, q in zip(point_times, point_values) if q >= floor]

    def visible_forecast_points(point_times: list[float], point_values: list[float], floor: float, mapper: Any) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for t, q in zip(point_times, point_values):
            if q < floor:
                break
            points.append((sx(t), mapper(q)))
        return points

    def visible_ratio_history(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if not ratio_axis:
            return []
        ratio_min, _ = ratio_axis
        return [(sx(t), sy_ratio(v)) for t, v in points if v >= ratio_min]

    def visible_ratio_forecast(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if not ratio_axis:
            return []
        ratio_min, _ = ratio_axis
        visible: list[tuple[float, float]] = []
        for t, v in points:
            if v < ratio_min:
                break
            visible.append((sx(t), sy_ratio(v)))
        return visible

    decade = y_min
    while decade <= y_max * 1.001:
        y = sy(decade)
        draw.line([(left, y), (right, y)], fill=(220, 220, 220), width=1)
        draw.text((24, y - 7), fmt_log_tick(decade), fill=(80, 80, 80), font=FONT_TINY)
        decade *= 10
    for year in range(0, int(math.ceil(x_max)) + 1, 5):
        x = sx(year)
        draw.line([(x, top), (x, bottom)], fill=(232, 232, 232), width=1)
        draw.text((x - 8, bottom + 8), str(year), fill=(80, 80, 80), font=FONT_TINY)
    draw.text((500, bottom + 28), "Years from first production month", fill=(70, 70, 70), font=FONT_SMALL)
    draw_vertical_text(img, (10, int((top + bottom) / 2) - 36), "Rate (LH)", FONT_SMALL, (70, 70, 70))
    if ratio_axis:
        ratio_min, ratio_max = ratio_axis
        tick = ratio_min
        while tick <= ratio_max * 1.001:
            y = sy_ratio(tick)
            draw.line([(right, y), (right + 4, y)], fill=(115, 115, 115), width=1)
            draw.text((right + 6, y - 7), fmt_log_tick(tick), fill=(80, 80, 80), font=FONT_TINY)
            tick *= 10
        draw_vertical_text(img, (right + 34, int((top + bottom) / 2) - 38), "Ratio (RH)", FONT_TINY, (70, 70, 70))

    if best and selected_fit_rates:
        primary_color = colors[primary]
        fit_pts = visible_history_points(times, selected_fit_rates, y_min, sy)
        draw_line(draw, fit_pts, primary_color, 1, dashed=True)

    for name, values_hist, future in (
        ("Oil", oil, oil_future),
        ("Gas", gas, gas_future),
        ("Water", water, water_future),
    ):
        pts = visible_history_points(times, values_hist, y_min, sy)
        if has_forecast or len(pts) >= 6:
            draw_line(draw, pts, colors[name], 3 if name == primary else 2)
        else:
            draw_markers(draw, pts, colors[name], 4 if name == primary else 3)
        if future:
            fpts = visible_forecast_points(future[0], future[1], y_min, sy)
            draw_line(draw, fpts, colors[name], 2, dashed=True)

    if ratio_axis:
        for ratio_name, ratio_hist, ratio_fcast, color in (
            ("GOR", hist_gor, fcast_gor, ratio_colors["GOR"]),
            (ratio_label, hist_wor_wgr, fcast_wor_wgr, ratio_colors["WOR_WGR"]),
        ):
            hpts = visible_ratio_history(ratio_hist)
            if has_forecast or len(hpts) >= 6:
                draw_line(draw, hpts, color, 2)
            else:
                draw_markers(draw, hpts, color, 3)
            fpts = visible_ratio_forecast(ratio_fcast)
            draw_line(draw, fpts, color, 2, dashed=True)

    legend_x = int(legend_config.get("x", 982))
    legend_line = int(legend_config.get("lineLength", 22))
    for idx, name in enumerate(("Oil", "Gas", "Water")):
        y = 126 + idx * 16
        draw.line([(legend_x, y), (legend_x + legend_line, y)], fill=colors[name], width=2)
        draw.text((legend_x + 28, y - 7), f"{name} (LH)", fill=(55, 55, 55), font=FONT_LEGEND)
    if ratio_axis:
        draw.line([(legend_x, 184), (legend_x + legend_line, 184)], fill=ratio_colors["GOR"], width=2)
        draw.text((legend_x + 28, 177), "GOR (RH)", fill=(55, 55, 55), font=FONT_LEGEND)
        draw.line([(legend_x, 200), (legend_x + legend_line, 200)], fill=ratio_colors["WOR_WGR"], width=2)
        draw.text((legend_x + 28, 193), f"{ratio_label} (RH)", fill=(55, 55, 55), font=FONT_LEGEND)
    if not has_forecast:
        style_y = 230 if ratio_axis else 184
        draw_markers(draw, [(legend_x + 11, style_y)], (40, 40, 40), 3)
        draw.text((legend_x + 28, style_y - 7), "history point", fill=(55, 55, 55), font=FONT_LEGEND)

    panel_y = 482
    draw.line([(50, panel_y - 18), (1070, panel_y - 18)], fill=(205, 205, 205), width=1)
    draw.text((58, panel_y), "Selected Methods", fill=(40, 40, 40), font=FONT_BOLD)
    method_lines = [
        f"Primary: {compact_method(summary['PrimaryMethodUsed'])} | RMSE {summary['PrimaryTailRMSE']}",
        f"Oil: {compact_method(oil_fit['method'] if oil_fit else 'not fitted')} | RMSE {fmt_metric(oil_fit.get('tail_rmse') if oil_fit else None)}",
        f"Gas: {compact_method(gas_fit['method'] if gas_fit else 'not fitted')} | RMSE {fmt_metric(gas_fit.get('tail_rmse') if gas_fit else None)}",
        f"Gas ratio: {compact_method(summary['GasRatioMethod'])} | R2 {summary['GasRatioTailR2']}",
        f"Water ratio: {compact_method(summary['WaterRatioMethod'])} | R2 {summary['WaterRatioTailR2']}",
    ]
    for i, text in enumerate(method_lines):
        draw.text((58, panel_y + 32 + i * 21), text[:48], fill=(65, 65, 65), font=FONT_SMALL)

    draw.text((420, panel_y), "Arps / Ratio Params", fill=(40, 40, 40), font=FONT_BOLD)
    if summary["PrimaryMethodUsed"] == "no DCA fit generated":
        param_lines = [
            "Primary Arps: n/a",
            "Insufficient data for DCA shape",
            "Type curve / offset proxy needed",
        ]
    else:
        primary_ratio_lines = []
        if summary["PrimaryProduct"] == "Oil":
            primary_ratio_lines = [
                f"GOR: {summary['GasRatioStart']} -> {summary['GasRatioEnd']}",
                f"WOR: {summary['WaterRatioStart']} -> {summary['WaterRatioEnd']}",
            ]
        else:
            primary_ratio_lines = [
                f"OGR: {summary['OilRatioStart']} -> {summary['OilRatioEnd']}",
                f"WGR: {summary['WaterRatioStart']} -> {summary['WaterRatioEnd']}",
            ]
        param_lines = [
            f"Qi: {summary['PrimaryProductQi']} | b: {summary['PrimaryBFactor']}",
            f"Di eff: {summary['PrimaryEffectiveAnnualDiPercent']}% | Dmin: {terminal_effective_decline() * 100:.1f}%",
            f"Recent months: {summary['RecentFitStartMonthIndex']}-{summary['RecentFitEndMonthIndex']}",
        ] + primary_ratio_lines
    for i, text in enumerate(param_lines):
        draw.text((420, panel_y + 32 + i * 21), text[:46], fill=(65, 65, 65), font=FONT_SMALL)

    draw.text((745, panel_y), "EUR Summary", fill=(40, 40, 40), font=FONT_BOLD)
    eur_lines = [
        f"Hist + Fcast Oil: {summary['EUR_Oil_BBL']:,.0f} bbl",
        f"Hist + Fcast Gas: {summary['EUR_Gas_MCF']:,.0f} mcf",
        f"EUR: {summary['EUR_MBOE_6to1']:,.1f} MBOE",
        f"Life @ {primary_life_limit_label(summary['PrimaryProduct'])}: {summary.get('TotalLifeYears', 'n/a')} yrs",
        f"EUR/ft: {summary['EUR_MBOEPerFT']:,.2f} MBOE/ft" if summary["EUR_MBOEPerFT"] else "EUR/ft: n/a",
    ]
    for i, text in enumerate(eur_lines):
        draw.text((745, panel_y + 32 + i * 21), text[:42], fill=(65, 65, 65), font=FONT_SMALL)

    qc_folder = summary.get("QC") if summary.get("QC") in {"Green", "Yellow", "Red"} else "Unclassified"
    chart_folder = CHART_DIR / qc_folder
    chart_folder.mkdir(parents=True, exist_ok=True)
    path = chart_folder / f"{clean_name(well)}_primary_product.png"
    margin = int(CHART_CONFIG["plot"].get("printMarginPx", 0))
    if margin > 0:
        img = ImageOps.expand(img, border=margin, fill="white")
    img.save(path)
    return path


def run_batch(production_zip: Path, wells_zip: Path, output_dir: Path, chart_config_path: Path | None = None) -> None:
    global OUTPUT_DIR, CHART_DIR, CHART_CONFIG
    OUTPUT_DIR = output_dir.resolve()
    CHART_DIR = OUTPUT_DIR / "primary_product_charts"
    CHART_CONFIG = load_chart_config(chart_config_path)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    by_well, metadata = normalize_inputs(production_zip.resolve(), wells_zip.resolve(), OUTPUT_DIR)
    profile = profile_and_recommend(str(OUTPUT_DIR / "normalized_production.csv"))
    (OUTPUT_DIR / "mcp_profile_and_recommendations.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    recommendation_by_well = {item["well"]: item for item in profile["recommendations"]}

    summary_rows: list[dict[str, Any]] = []
    method_rows: list[dict[str, Any]] = []
    chart_count = 0

    for well in sorted(by_well):
        rows = by_well[well]
        times = elapsed_years(rows)
        oil_rates = [r["oil_bopd"] for r in rows]
        gas_rates = [r["gas_mcfd"] for r in rows]
        water_rates = [r["water_bwpd"] for r in rows]
        hist_oil = sum(r["oil_bbl"] for r in rows)
        hist_gas = sum(r["gas_mcf"] for r in rows)
        oil_boe = hist_oil
        gas_boe = hist_gas / 6.0
        primary = "Gas" if gas_boe > oil_boe * 1.15 else "Oil"
        primary_rates = gas_rates if primary == "Gas" else oil_rates
        primary_positive_months = len([rate for rate in primary_rates if rate > 0])

        oil_fit, oil_candidates = choose_fit(times, oil_rates)
        gas_fit, gas_candidates = choose_fit(times, gas_rates)
        for product, candidates in (("Oil", oil_candidates), ("Gas", gas_candidates)):
            for candidate in candidates:
                method_rows.append(
                    {
                        "WellName": well,
                        "Product": product,
                        "CandidateMethod": candidate["method"],
                        "TailWAPEPercent": round(candidate["tail_wape"] * 100.0, 2) if candidate["tail_wape"] is not None else "",
                        "TailRMSE": round(candidate["tail_rmse"], 6) if candidate["tail_rmse"] is not None else "",
                        "TailR2": round(candidate["tail_r2"], 6) if candidate["tail_r2"] is not None else "",
                        "FitWAPEPercent": round(candidate["fit_wape"] * 100.0, 2) if candidate["fit_wape"] is not None else "",
                        "FitRMSE": round(candidate["fit_rmse"], 6) if candidate["fit_rmse"] is not None else "",
                        "FitR2": round(candidate["fit_r2"], 6) if candidate["fit_r2"] is not None else "",
                        "Qi": round(candidate["qi"], 6),
                        "NominalDiAnnual": round(candidate["di_nominal_annual"], 6),
                        "EffectiveAnnualDi": round(candidate["annual_di_effective"], 6),
                        "BFactor": candidate["b"],
                        "OriginMonthIndex": candidate["origin_index"] + 1,
                        "RecentFitStartMonthIndex": candidate["tail_start_index"] + 1,
                        "RecentFitEndMonthIndex": candidate["tail_end_index"] + 1,
                    }
                )

        best = gas_fit if primary == "Gas" else oil_fit
        oil_future = gas_future = water_future = None
        gas_ratio_method = water_ratio_method = "n/a"
        gas_ratio_wape = water_ratio_wape = None
        gas_ratio_rmse = water_ratio_rmse = None
        gas_ratio_r2 = water_ratio_r2 = None
        gas_ratio_start = gas_ratio_end = None
        oil_ratio_start = oil_ratio_end = None
        water_ratio_start = water_ratio_end = None
        forecast_oil = forecast_gas = 0.0

        if best:
            future_t, primary_future_rates = forecast_series(best, times)
            if primary == "Oil":
                oil_future = (future_t, primary_future_rates)
                gor_model = smooth_ratio_model(times, gas_rates, oil_rates, "GOR")
                wor_model = smooth_ratio_model(times, water_rates, oil_rates, "WOR")
                gas_future = trim_forecast_tail(future_t, [q * gor_model["predict"](t) for t, q in zip(future_t, primary_future_rates)])
                water_future = trim_forecast_tail(future_t, [q * wor_model["predict"](t) for t, q in zip(future_t, primary_future_rates)])
                gas_ratio_method = gor_model["method"]
                water_ratio_method = wor_model["method"]
                gas_ratio_wape = gor_model["tail_wape"]
                water_ratio_wape = wor_model["tail_wape"]
                gas_ratio_rmse = gor_model["tail_rmse"]
                water_ratio_rmse = wor_model["tail_rmse"]
                gas_ratio_r2 = gor_model["tail_r2"]
                water_ratio_r2 = wor_model["tail_r2"]
                gas_ratio_start, gas_ratio_end = ratio_bounds(gas_future, oil_future)
                water_ratio_start, water_ratio_end = ratio_bounds(water_future, oil_future)
            else:
                gas_future = (future_t, primary_future_rates)
                ogr_model = smooth_ratio_model(times, oil_rates, gas_rates, "OGR")
                wgr_model = smooth_ratio_model(times, water_rates, gas_rates, "WGR")
                oil_future = trim_forecast_tail(future_t, [q * ogr_model["predict"](t) for t, q in zip(future_t, primary_future_rates)])
                water_future = trim_forecast_tail(future_t, [q * wgr_model["predict"](t) for t, q in zip(future_t, primary_future_rates)])
                gas_ratio_method = "primary gas DCA"
                water_ratio_method = wgr_model["method"]
                gas_ratio_wape = best["tail_wape"]
                water_ratio_wape = wgr_model["tail_wape"]
                gas_ratio_rmse = best["tail_rmse"]
                water_ratio_rmse = wgr_model["tail_rmse"]
                gas_ratio_r2 = best["tail_r2"]
                water_ratio_r2 = wgr_model["tail_r2"]
                oil_ratio_start, oil_ratio_end = ratio_bounds(oil_future, gas_future)
                water_ratio_start, water_ratio_end = ratio_bounds(water_future, gas_future)
            forecast_oil = remaining_volume(oil_future[1]) if oil_future else 0.0
            forecast_gas = remaining_volume(gas_future[1]) if gas_future else 0.0

        rec = recommendation_by_well.get(well, {})
        qc = (rec.get("qc") or "yellow").capitalize()
        fit_warning = recent_fit_warning(best, primary_rates)
        if not best:
            qc = "Red"
        elif best.get("tail_wape") is not None and best["tail_wape"] > float(CHART_CONFIG["forecast"].get("redTailWapeThreshold", 0.60)):
            qc = "Red"
        elif fit_warning:
            qc = "Yellow" if qc == "Green" else qc
        lifecycle_stage, data_sufficiency, type_curve_status = classify_lifecycle(primary_positive_months, best)

        lateral = metadata.get(well, {}).get("LateralLength_FT")
        eur_oil = hist_oil + forecast_oil
        eur_gas = hist_gas + forecast_gas
        eur_mboe = (eur_oil + eur_gas / 6.0) / 1000.0
        eur_per_ft = eur_mboe / lateral if lateral and lateral > 0 else None
        projection_end_years = total_life_years(times, oil_future, gas_future, water_future)
        primary_future = gas_future if primary == "Gas" else oil_future
        total_life = primary_life_years(times, primary, primary_future)
        summary = {
            "WellName": well,
            "QC": qc,
            "McpQcStatus": (rec.get("qc") or "").capitalize(),
            "PrimaryProduct": primary,
            "LifecycleStage": lifecycle_stage,
            "PrimaryPositiveMonths": primary_positive_months,
            "DcaDataSufficiency": data_sufficiency,
            "TypeCurveProxyStatus": type_curve_status,
            "RecentFitWarning": fit_warning,
            "RecommendedMethodFamily": rec.get("recommendedMethod") or "",
            "PrimaryMethodUsed": best["method"] if best else "no DCA fit generated",
            "ForecastSelectionBasis": best.get("selection_basis", "") if best else "no DCA fit generated",
            "AlternateRecentTailMethod": best.get("alternate_recent_method", "") if best else "",
            "AlternateRecentTailWAPEPercent": round(best["alternate_recent_tail_wape"] * 100.0, 2)
            if best and best.get("alternate_recent_tail_wape") is not None
            else "",
            "PrimaryForecastVolumeDeltaVsRecentTail": round(best.get("forecast_volume_delta_vs_recent", 0.0), 2)
            if best and best.get("forecast_volume_delta_vs_recent") is not None
            else "",
            "PressureDataAvailable": "No",
            "DataCadence": "monthly",
            "PrimaryTailWAPEPercent": round(best["tail_wape"] * 100.0, 2) if best and best.get("tail_wape") is not None else "",
            "PrimaryTailRMSE": fmt_metric(best.get("tail_rmse") if best else None),
            "PrimaryTailR2": fmt_metric(best.get("tail_r2") if best else None, 3),
            "RecentFitStartMonthIndex": best["tail_start_index"] + 1 if best else "",
            "RecentFitEndMonthIndex": best["tail_end_index"] + 1 if best else "",
            "RecentFitStartYear": round(best["tail_start_year"], 6) if best else "",
            "RecentFitEndYear": round(best["tail_end_year"], 6) if best else "",
            "PrimaryProductQi": round(best["qi"], 6) if best else "",
            "PrimaryNominalDiAnnual": round(best["di_nominal_annual"], 6) if best else "",
            "PrimaryEffectiveAnnualDiPercent": round(best["annual_di_effective"] * 100.0, 2) if best else "",
            "PrimaryBFactor": best["b"] if best else "",
            "GasRatioMethod": gas_ratio_method,
            "GasRatioTailWAPEPercent": round(gas_ratio_wape * 100.0, 2) if gas_ratio_wape is not None else "",
            "GasRatioTailRMSE": fmt_metric(gas_ratio_rmse),
            "GasRatioTailR2": fmt_metric(gas_ratio_r2, 3),
            "GasRatioStart": fmt_metric(gas_ratio_start, 3),
            "GasRatioEnd": fmt_metric(gas_ratio_end, 3),
            "OilRatioStart": fmt_metric(oil_ratio_start, 4),
            "OilRatioEnd": fmt_metric(oil_ratio_end, 4),
            "WaterRatioMethod": water_ratio_method,
            "WaterRatioTailWAPEPercent": round(water_ratio_wape * 100.0, 2) if water_ratio_wape is not None else "",
            "WaterRatioTailRMSE": fmt_metric(water_ratio_rmse),
            "WaterRatioTailR2": fmt_metric(water_ratio_r2, 3),
            "WaterRatioStart": fmt_metric(water_ratio_start, 3),
            "WaterRatioEnd": fmt_metric(water_ratio_end, 3),
            "HistOil_BBL": round(hist_oil, 2),
            "ForecastOil_BBL_30yr_DCA": round(forecast_oil, 2),
            "EUR_Oil_BBL": round(eur_oil, 2),
            "HistGas_MCF": round(hist_gas, 2),
            "ForecastGas_MCF_30yr_DCA": round(forecast_gas, 2),
            "EUR_Gas_MCF": round(eur_gas, 2),
            "EUR_MBOE_6to1": round(eur_mboe, 3),
            "TotalLifeYears": round(total_life, 2),
            "ProjectionEndYears": round(projection_end_years, 2),
            "LateralLength_FT": lateral or "",
            "EUR_MBOEPerFT": round(eur_per_ft, 6) if eur_per_ft is not None else "",
            "ChartPath": "",
        }
        chart_path = write_chart(well, rows, primary, best, oil_fit, gas_fit, oil_future, gas_future, water_future, summary)
        summary["ChartPath"] = str(chart_path.relative_to(OUTPUT_DIR))
        summary_rows.append(summary)
        chart_count += 1

    analog_rows = build_analog_screen(summary_rows, metadata)
    summary_fields = list(summary_rows[0].keys())
    with (OUTPUT_DIR / "well_forecast_summary_green_yellow_red.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)
    (OUTPUT_DIR / "well_forecast_summary_green_yellow_red.json").write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")

    method_fields = list(method_rows[0].keys()) if method_rows else ["WellName"]
    with (OUTPUT_DIR / "best_method_selection_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=method_fields)
        writer.writeheader()
        writer.writerows(method_rows)

    analog_fields = list(analog_rows[0].keys()) if analog_rows else [
        "TargetWellName",
        "AnalogWellName",
        "PrimaryProduct",
        "ReservoirKey",
        "DistanceMiles",
        "TargetLateralLength_FT",
        "AnalogLateralLength_FT",
        "LateralRatio",
        "AnalogQC",
        "AnalogMethod",
        "AnalogTailWAPEPercent",
        "AnalogEUR_MBOEPerFT",
        "AnalogScore",
    ]
    with (OUTPUT_DIR / "analog_type_curve_screen.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=analog_fields)
        writer.writeheader()
        writer.writerows(analog_rows)

    qc_counts = Counter(row["QC"] for row in summary_rows)
    primary_counts = Counter(row["PrimaryProduct"] for row in summary_rows)
    lifecycle_counts = Counter(row["LifecycleStage"] for row in summary_rows)
    method_counts = Counter(row["PrimaryMethodUsed"] for row in summary_rows)
    run_summary = {
        "source": "tauris-skills only",
        "wellCount": len(summary_rows),
        "chartCount": chart_count,
        "qcCounts": dict(qc_counts),
        "primaryProductCounts": dict(primary_counts),
        "lifecycleStageCounts": dict(lifecycle_counts),
        "primaryMethodCounts": dict(method_counts),
        "analogTypeCurveScreenRows": len(analog_rows),
        "normalization": "Monthly production volumes divided by reported ProducingDays; no fixed 30.4-day divisor.",
        "methodLimit": "The current tauris-skills MCP is a profiler/recommender, so this batch runner uses repo-local monthly DCA candidates only. Prophet/external C# engines were not used.",
        "chartConfig": display_path(chart_config_path.resolve()) if chart_config_path else "built-in defaults",
        "outputFolder": str(OUTPUT_DIR),
    }
    (OUTPUT_DIR / "forecast_batch_run_summary.json").write_text(json.dumps(run_summary, indent=2), encoding="utf-8")
    md_lines = [
        "# Monthly Production DCA Batch",
        "",
        "This run used only code under `tauris-skills/areas/forecasting/mcp-servers/forecasting-mcp`.",
        "",
        f"- Wells: {len(summary_rows)}",
        f"- Charts: {chart_count}",
        f"- QC counts: {dict(qc_counts)}",
        f"- Primary products: {dict(primary_counts)}",
        f"- Lifecycle stages: {dict(lifecycle_counts)}",
        f"- Analog type-curve screen rows: {len(analog_rows)}",
        "- Input normalization: monthly volumes divided by reported `ProducingDays`; no fixed 30.4-day divisor.",
        "- Pressure data: none in the monthly production upload; pressure-aware hybrid methods are disabled.",
        "- Forecast method: repo-local monthly DCA candidate selection using Arps exponential/hyperbolic fits and tail WAPE.",
        "- Prophet/external C# engines: not used in this run.",
    ]
    (OUTPUT_DIR / "RUN_SUMMARY.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps(run_summary, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repo-local monthly production DCA screening, charts, and summary exports.")
    parser.add_argument("--production-zip", type=Path, default=DEFAULT_PRODUCTION_ZIP, help="Zip containing one monthly production CSV.")
    parser.add_argument("--wells-zip", type=Path, default=DEFAULT_WELLS_ZIP, help="Zip containing one well metadata CSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output folder to rebuild.")
    parser.add_argument("--chart-config", type=Path, default=DEFAULT_CHART_CONFIG, help="Chart and batch settings JSON.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_batch(args.production_zip, args.wells_zip, args.output_dir, args.chart_config)
