#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("areas/forecasting/mcp-servers/forecasting-mcp/data/input/synthetic_unconventional_daily.csv")
DEFAULT_PROFILE = Path("areas/forecasting/mcp-servers/forecasting-mcp/data/output/synthetic_unconventional_daily_profile.json")
DEFAULT_OUTPUT = Path("areas/forecasting/mcp-servers/forecasting-mcp/data/output/plots")
DEFAULT_CONFIG = Path("areas/forecasting/mcp-servers/forecasting-mcp/chart_config.default.json")


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value: str) -> datetime:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(value)


def slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def load_rows(path: Path) -> dict[str, list[dict[str, Any]]]:
    by_well: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            well = row.get("Entity Name", "").strip()
            if well:
                by_well[well].append(row)
    for rows in by_well.values():
        rows.sort(key=lambda row: parse_date(row["Date"]))
    return by_well


def load_profile(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["well"]: item for item in data["profiles"]}


def load_recommendations(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["well"]: item for item in data["recommendations"]}


def load_chart_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def series_points(rows: list[dict[str, Any]], column: str) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    for index, row in enumerate(rows):
        value = parse_float(row.get(column))
        if value is not None and value >= 0:
            points.append((index, value))
    return points


def log10_safe(value: float) -> float:
    return math.log10(max(value, 0.001))


def value_from_log(log_value: float) -> float:
    return 10**log_value


def point_xy(
    index: float,
    value: float,
    x_min: float,
    x_max: float,
    log_y_min: float,
    log_y_max: float,
    left: int,
    width: int,
    top: int,
    height: int,
) -> tuple[float, float] | None:
    if value <= 0 or index < x_min or index > x_max:
        return None
    x_denom = max(x_max - x_min, 1e-9)
    y_denom = max(log_y_max - log_y_min, 1e-9)
    x = left + ((index - x_min) / x_denom) * width
    y = top + height - ((log10_safe(value) - log_y_min) / y_denom) * height
    return x, y


def path_for(
    points: list[tuple[float, float]],
    x_min: float,
    x_max: float,
    log_y_min: float,
    log_y_max: float,
    left: int,
    width: int,
    top: int,
    height: int,
) -> str:
    if not points:
        return ""
    commands = []
    for index, value in points:
        xy = point_xy(index, value, x_min, x_max, log_y_min, log_y_max, left, width, top, height)
        if xy is None:
            continue
        x, y = xy
        commands.append(("M" if not commands else "L") + f"{x:.2f},{y:.2f}")
    return " ".join(commands)


def arps_hyp_to_exp_rate(qi: float, nominal_di_annual: float, b_factor: float, terminal_di_annual: float, years: float) -> float:
    years = max(years, 0.0)
    qi = max(qi, 0.001)
    nominal_di_annual = max(nominal_di_annual, 1e-9)
    terminal_di_annual = max(terminal_di_annual, 1e-9)
    b_factor = max(b_factor, 0.0)
    if b_factor < 1e-9:
        return qi * math.exp(-max(nominal_di_annual, terminal_di_annual) * years)

    transition_years = max((nominal_di_annual / terminal_di_annual - 1.0) / (b_factor * nominal_di_annual), 0.0)
    if years <= transition_years:
        return qi / ((1.0 + b_factor * nominal_di_annual * years) ** (1.0 / b_factor))

    transition_rate = qi / ((1.0 + b_factor * nominal_di_annual * transition_years) ** (1.0 / b_factor))
    return transition_rate * math.exp(-terminal_di_annual * (years - transition_years))


def fit_arps_hyp_to_exp(
    points: list[tuple[int, float]],
    origin_index: int,
    x_max: float,
    visual_terminal_rate: float | None = None,
) -> dict[str, Any] | None:
    fit_points = [(index, value) for index, value in points if index >= origin_index and value > 0]
    if len(fit_points) < 12:
        return None

    terminal_di_annual = 0.08
    candidates: list[dict[str, Any]] = []
    for b_factor in (0.2, 0.5, 0.8, 1.0, 1.2):
        for nominal_di_annual in (0.25, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 2.8):
            residuals = []
            shapes = []
            for index, value in fit_points:
                years = (index - origin_index) / 365.25
                shape = arps_hyp_to_exp_rate(1.0, nominal_di_annual, b_factor, terminal_di_annual, years)
                if shape <= 0:
                    continue
                shapes.append((value, shape))
                residuals.append(math.log(value) - math.log(shape))
            if not residuals:
                continue
            log_qi = sum(residuals) / len(residuals)
            qi = math.exp(log_qi)
            actual_logs = [math.log(value) for value, _shape in shapes]
            predicted_logs = [math.log(qi * shape) for _value, shape in shapes]
            errors = [(actual - predicted) ** 2 for actual, predicted in zip(actual_logs, predicted_logs)]
            rmse = math.sqrt(sum(errors) / len(errors))
            mean_log = sum(actual_logs) / len(actual_logs)
            total_sum_squares = sum((actual - mean_log) ** 2 for actual in actual_logs)
            residual_sum_squares = sum(errors)
            log_r2 = 1.0 - residual_sum_squares / total_sum_squares if total_sum_squares > 1e-12 else 1.0
            candidates.append(
                {
                    "qi": qi,
                    "nominalDiAnnual": nominal_di_annual,
                    "bFactor": b_factor,
                    "terminalDiAnnual": terminal_di_annual,
                    "logRmse": rmse,
                    "logR2": max(min(log_r2, 1.0), -9.999),
                }
            )
    if not candidates:
        return None

    best = min(candidates, key=lambda item: item["logRmse"])
    if best["logR2"] >= 0.95:
        best["quality"] = "excellent"
    elif best["logR2"] >= 0.85:
        best["quality"] = "good"
    elif best["logR2"] >= 0.70:
        best["quality"] = "review"
    else:
        best["quality"] = "poor"
    curve_points = []
    end_index = int(max(x_max, fit_points[-1][0]))
    step = 15 if end_index - origin_index <= 1200 else 30
    hit_terminal = False
    for index in range(origin_index, end_index + 1, step):
        years = (index - origin_index) / 365.25
        rate = arps_hyp_to_exp_rate(
            best["qi"],
            best["nominalDiAnnual"],
            best["bFactor"],
            best["terminalDiAnnual"],
            years,
        )
        if visual_terminal_rate is not None and rate <= visual_terminal_rate:
            hit_terminal = True
            break
        curve_points.append((float(index), rate))
    best["points"] = curve_points
    return best


def arps_fit_svg_path(
    points: list[tuple[int, float]],
    origin_index: int,
    x_min: float,
    x_max: float,
    log_y_min: float,
    log_y_max: float,
    plot_left: int,
    plot_width: int,
    plot_top: int,
    plot_height: int,
    visual_terminal_rate: float | None = None,
) -> tuple[dict[str, Any] | None, str]:
    fit = fit_arps_hyp_to_exp(points, origin_index, x_max, visual_terminal_rate=visual_terminal_rate)
    if not fit:
        return None, ""
    return fit, path_for(fit["points"], x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)


def _linear_fit(points: list[tuple[float, float]]) -> dict[str, float]:
    n = len(points)
    if n == 0:
        return {"intercept": 0.0, "slope": 0.0, "rmse": 0.0}
    x_mean = sum(point[0] for point in points) / n
    y_mean = sum(point[1] for point in points) / n
    denom = sum((point[0] - x_mean) ** 2 for point in points)
    slope = 0.0 if denom <= 1e-12 else sum((point[0] - x_mean) * (point[1] - y_mean) for point in points) / denom
    slope = min(slope, 0.0)
    intercept = y_mean - slope * x_mean
    rmse = math.sqrt(sum((point[1] - (intercept + slope * point[0])) ** 2 for point in points) / n)
    return {"intercept": intercept, "slope": slope, "rmse": rmse}


def _eval_ratio_fit(fit: dict[str, Any], years: float) -> float:
    stages = fit["stages"]
    if fit["stageCount"] == 1 or years <= fit["splitYears"]:
        stage = stages[0]
    else:
        stage = stages[1]
    return math.exp(stage["intercept"] + stage["slope"] * years)


def fit_ratio_profile(
    numerator_points: list[tuple[int, float]],
    oil_points: list[tuple[int, float]],
    origin_index: int,
    ratio_name: str,
    min_points: int = 24,
) -> dict[str, Any] | None:
    oil_by_index = {index: value for index, value in oil_points if value > 0}
    ratio_points = []
    for index, numerator in numerator_points:
        oil_value = oil_by_index.get(index)
        if oil_value is None or oil_value <= 0 or numerator <= 0 or index < origin_index:
            continue
        years = (index - origin_index) / 365.25
        ratio_points.append((years, math.log(numerator / oil_value)))
    if len(ratio_points) < min_points:
        return None

    one_stage = _linear_fit(ratio_points)
    best: dict[str, Any] = {
        "ratioName": ratio_name,
        "stageCount": 1,
        "splitYears": None,
        "rmse": one_stage["rmse"],
        "stages": [one_stage],
    }

    if len(ratio_points) >= min_points * 2:
        best_two_stage: dict[str, Any] | None = None
        for split_fraction in (0.35, 0.5, 0.65):
            split_index = max(min_points, min(len(ratio_points) - min_points, int(len(ratio_points) * split_fraction)))
            left = ratio_points[:split_index]
            right = ratio_points[split_index:]
            left_fit = _linear_fit(left)
            right_fit = _linear_fit(right)
            rmse = math.sqrt(
                (
                    sum((point[1] - (left_fit["intercept"] + left_fit["slope"] * point[0])) ** 2 for point in left)
                    + sum((point[1] - (right_fit["intercept"] + right_fit["slope"] * point[0])) ** 2 for point in right)
                )
                / len(ratio_points)
            )
            candidate = {
                "ratioName": ratio_name,
                "stageCount": 2,
                "splitYears": ratio_points[split_index][0],
                "rmse": rmse,
                "stages": [left_fit, right_fit],
            }
            if best_two_stage is None or candidate["rmse"] < best_two_stage["rmse"]:
                best_two_stage = candidate
        if best_two_stage and best_two_stage["rmse"] < one_stage["rmse"] * 0.85:
            best = best_two_stage

    best["latestRatio"] = math.exp(ratio_points[-1][1])
    return best


def ratio_derived_rate_path(
    oil_fit: dict[str, Any] | None,
    ratio_fit: dict[str, Any] | None,
    origin_index: int,
    visual_terminal_rate: float,
) -> list[tuple[float, float]]:
    if not oil_fit or not ratio_fit:
        return []
    derived = []
    for index, oil_rate in oil_fit["points"]:
        years = (index - origin_index) / 365.25
        ratio = _eval_ratio_fit(ratio_fit, years)
        rate = oil_rate * ratio
        if rate <= visual_terminal_rate:
            break
        derived.append((index, rate))
    return derived


def log_grid(log_y_min: float, log_y_max: float, left: int, width: int, top: int, height: int) -> str:
    lines = []
    start_decade = math.floor(log_y_min)
    end_decade = math.ceil(log_y_max)
    for decade in range(start_decade, end_decade + 1):
        for multiplier in range(1, 10):
            log_value = decade + math.log10(multiplier)
            if log_value < log_y_min or log_value > log_y_max:
                continue
            y = top + height - ((log_value - log_y_min) / max(log_y_max - log_y_min, 1e-9)) * height
            major = multiplier == 1
            if not major:
                continue
            stroke = "#111"
            opacity = "0.7"
            width_attr = "1.1"
            lines.append(
                f'<line x1="{left}" y1="{y:.2f}" x2="{left + width}" y2="{y:.2f}" '
                f'stroke="{stroke}" stroke-width="{width_attr}" opacity="{opacity}" />'
            )
            if major:
                label = f"{value_from_log(log_value):.0f}"
                lines.append(
                    f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" font-family="Arial" font-size="11" fill="#333">{label}</text>'
                )
    return "".join(lines)


def x_grid(x_min: float, x_max: float, center_index: float, left: int, width: int, top: int, height: int) -> str:
    lines = []
    span = max(x_max - x_min, 1)
    step = 30 if span <= 240 else 90
    first_relative = math.ceil((x_min - center_index) / step) * step
    value = center_index + first_relative
    if abs(value - center_index) > 1e-6 and value > center_index:
        value -= step
    while value <= x_max:
        x = left + ((value - x_min) / span) * width
        relative = int(round(value - center_index))
        is_zero = abs(relative) == 0
        stroke = "#000" if is_zero else "#999"
        stroke_width = "1.6" if is_zero else "0.7"
        opacity = "0.85" if is_zero else "0.25"
        label = "Time 0" if is_zero else f"{relative:+d}"
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + height}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}" />')
        lines.append(f'<text x="{x:.2f}" y="{top + height + 18}" text-anchor="middle" font-family="Arial" font-size="11" fill="#333">{label}</text>')
        value += step
    return "".join(lines)


def x_grid_calendar(
    x_min: float,
    x_max: float,
    start_date: datetime,
    forecast_origin_index: float,
    left: int,
    width: int,
    top: int,
    height: int,
) -> str:
    lines = []
    span = max(x_max - x_min, 1)
    axis_start_date = start_date + timedelta(days=x_min)
    end_date = start_date + timedelta(days=x_max)
    step_years = 5

    first_year = (axis_start_date.year // step_years) * step_years
    if first_year < axis_start_date.year:
        first_year += step_years

    origin_x = left + ((forecast_origin_index - x_min) / span) * width
    lines.append(
        f'<line x1="{origin_x:.2f}" y1="{top}" x2="{origin_x:.2f}" y2="{top + height}" '
        'stroke="#000" stroke-width="1.6" opacity="0.85" />'
    )
    lines.append(
        f'<text x="{origin_x:.2f}" y="{top + height + 18}" text-anchor="middle" '
        'font-family="Arial" font-size="11" font-weight="700" fill="#000">FCAST</text>'
    )

    for year in range(first_year, end_date.year + step_years, step_years):
        tick_date = datetime(year, 1, 1)
        day_index = (tick_date - start_date).days
        if day_index < x_min or day_index > x_max:
            continue
        x = left + ((day_index - x_min) / span) * width
        is_decade = year % 10 == 0
        stroke = "#111" if is_decade else "#999"
        stroke_width = "1.1" if is_decade else "0.7"
        opacity = "0.45" if is_decade else "0.25"
        label = f"{year % 100:02d}"
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + height}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}" />'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{top + height + 18}" text-anchor="middle" '
            f'font-family="Arial" font-size="11" fill="#333">{label}</text>'
        )
    return "".join(lines)


def dominant_interpretation(profile: dict[str, Any]) -> str:
    diagnostics = profile.get("pressureProjectionDiagnostics", [])
    priority = [
        "possible_constraint_or_operational_issue",
        "drawdown_or_recompletion_response",
        "operationally_unstable",
        "hidden_depletion_risk",
        "depletion_supported",
    ]
    interpretations = {item["interpretation"] for item in diagnostics}
    for item in priority:
        if item in interpretations:
            return item
    return "no_pressure_diagnostic"


def forecast_quality_status(oil_fit: dict[str, Any] | None, gor_fit: dict[str, Any] | None, wor_fit: dict[str, Any] | None) -> dict[str, str]:
    if not oil_fit:
        return {"status": "red", "label": "No oil fit", "color": "#b00020"}
    log_r2 = float(oil_fit.get("logR2", 0.0))
    ratio_review = any(fit and fit.get("stageCount") == 2 for fit in (gor_fit, wor_fit))
    if log_r2 >= 0.95 and not ratio_review:
        return {"status": "green", "label": "Green", "color": "#008000"}
    if log_r2 >= 0.85:
        return {"status": "yellow", "label": "Yellow", "color": "#c58a00"}
    return {"status": "red", "label": "Red", "color": "#b00020"}


def arps_equation_box(
    effective_date: datetime,
    oil_fit: dict[str, Any] | None,
    gor_fit: dict[str, Any] | None,
    wor_fit: dict[str, Any] | None,
    left: int,
    top: int,
) -> str:
    quality = forecast_quality_status(oil_fit, gor_fit, wor_fit)
    oil_r2 = float(oil_fit.get("logR2", 0.0)) if oil_fit else 0.0
    oil_rmse = float(oil_fit.get("logRmse", 0.0)) if oil_fit else 0.0
    lines = [
        f'Forecast parameters ({quality["label"]}; Oil log R2={oil_r2:.2f}; RMSE={oil_rmse:.2f})',
        f"Effective date: {effective_date.date().isoformat()}",
    ]
    if oil_fit:
        lines.append(
            f'Oil: qi={oil_fit["qi"]:.1f}, Di={oil_fit["nominalDiAnnual"]:.2f}/yr, '
            f'b={oil_fit["bFactor"]:.1f}, Dmin={oil_fit["terminalDiAnnual"]:.2f}/yr'
        )
    else:
        lines.append("Oil: no fit")

    for label, fit, unit_scale, unit_label in (
        ("GOR", gor_fit, 1000.0, "scf/bbl"),
        ("WOR", wor_fit, 1.0, "bbl/bbl"),
    ):
        if not fit:
            lines.append(f"{label}: no ratio fit")
            continue
        latest = fit["latestRatio"] * unit_scale
        lines.append(f'{label}: {fit["stageCount"]}-stage ratio, latest={latest:.1f} {unit_label}')

    text_lines = []
    for index, line in enumerate(lines):
        weight = "700" if index == 0 else "400"
        fill = quality["color"] if index == 0 else "#111"
        text_lines.append(
            f'<text x="{left + 10}" y="{top + 18 + index * 16}" font-family="Arial" '
            f'font-size="11" font-weight="{weight}" fill="{fill}">{line}</text>'
        )
    height = 20 + len(lines) * 16
    return (
        f'<rect x="{left}" y="{top}" width="520" height="{height}" fill="#fff" '
        f'stroke="#111" opacity="0.92" />'
        + "".join(text_lines)
    )


def daily_history_cum(points: list[tuple[int, float]]) -> float:
    return sum(value for _index, value in points if value > 0)


def forecast_cum(points: list[tuple[float, float]], start_index: float) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x2 <= start_index or x2 <= x1:
            continue
        clipped_x1 = max(x1, start_index)
        if clipped_x1 > x1:
            fraction = (clipped_x1 - x1) / (x2 - x1)
            y1 = y1 + (y2 - y1) * fraction
            x1 = clipped_x1
        total += max(x2 - x1, 0.0) * (max(y1, 0.0) + max(y2, 0.0)) / 2.0
    return total


def cumulative_volume_box(
    oil: list[tuple[int, float]],
    gas: list[tuple[int, float]],
    water: list[tuple[int, float]],
    oil_forecast: list[tuple[float, float]],
    gas_forecast: list[tuple[float, float]],
    water_forecast: list[tuple[float, float]],
    forecast_start_index: float,
    left: int,
    top: int,
) -> str:
    oil_hist = daily_history_cum(oil) / 1_000_000.0
    oil_fcst = forecast_cum(oil_forecast, forecast_start_index) / 1_000_000.0
    gas_hist = daily_history_cum(gas) / 1_000.0
    gas_fcst = forecast_cum(gas_forecast, forecast_start_index) / 1_000.0
    water_hist = daily_history_cum(water) / 1_000_000.0
    water_fcst = forecast_cum(water_forecast, forecast_start_index) / 1_000_000.0
    lines = [
        "Cumulative volumes",
        f"Oil: Hist {oil_hist:.2f} MMBBL | Fcst {oil_fcst:.2f} | EUR {oil_hist + oil_fcst:.2f}",
        f"Gas: Hist {gas_hist:.1f} MMCF | Fcst {gas_fcst:.1f} | EUR {gas_hist + gas_fcst:.1f}",
        f"Water: Hist {water_hist:.2f} MMBBL | Fcst {water_fcst:.2f} | EUR {water_hist + water_fcst:.2f}",
    ]
    text_lines = []
    for index, line in enumerate(lines):
        weight = "700" if index == 0 else "400"
        text_lines.append(
            f'<text x="{left + 10}" y="{top + 18 + index * 16}" font-family="Arial" '
            f'font-size="11" font-weight="{weight}" fill="#111">{line}</text>'
        )
    height = 20 + len(lines) * 16
    return (
        f'<rect x="{left}" y="{top}" width="430" height="{height}" fill="#fff" '
        f'stroke="#111" opacity="0.92" />'
        + "".join(text_lines)
    )


def render_svg(
    well: str,
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    recommendation: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> str:
    config = config or load_chart_config(DEFAULT_CONFIG)
    plot_config = config["plot"]
    series_config = config["series"]
    guide_config = config["guides"]
    width = int(plot_config["width"])
    height = int(plot_config["height"])
    plot_top = int(plot_config["top"])
    plot_height = int(plot_config["plotHeight"])
    plot_width = int(plot_config["plotWidth"])
    plot_left = int(plot_config["left"])
    configured_forecast_days = int(plot_config["forecastDays"])
    min_history_days = int(plot_config["minHistoryDays"])
    show_synthetic_events = bool(plot_config.get("showSyntheticEvents", False))
    full_data_view = bool(plot_config.get("fullDataView", False))
    if full_data_view:
        forecast_days = int(float(plot_config.get("forecastYears", 30)) * 365.25)
    else:
        forecast_days = min(configured_forecast_days, max(min_history_days, len(rows) // 3))

    oil = series_points(rows, series_config["oil"]["column"])
    gas = series_points(rows, series_config["gas"]["column"])
    water = series_points(rows, series_config["water"]["column"])
    casing = series_points(rows, series_config["casingPressure"]["column"])
    tubing = series_points(rows, series_config["tubingPressure"]["column"])
    pip = series_points(rows, series_config["pumpIntakePressure"]["column"])

    last_oil = oil[-1] if oil else None
    center_index = last_oil[0] if last_oil else max(len(rows) - 1, 0)
    center_rate = last_oil[1] if last_oil else 100.0
    if full_data_view:
        first_date = parse_date(rows[0]["Date"]) if rows else datetime(2020, 1, 1)
        axis_start_months_before_first_prod = int(plot_config.get("axisStartMonthsBeforeFirstProduction", 12))
        axis_span_years = float(plot_config.get("axisSpanYears", 30))
        x_min = -axis_start_months_before_first_prod * 365.25 / 12.0
        x_max = x_min + axis_span_years * 365.25
        forecast_days = max(1, int(x_max - center_index))
    else:
        half_window = max(forecast_days, min(center_index, forecast_days))
        x_min = max(0.0, center_index - half_window)
        x_max = center_index + half_window

    if full_data_view:
        visible_values = [
            value
            for points in (oil, gas, water, casing, tubing, pip)
            for index, value in points
            if x_min <= index <= x_max and value > 0
        ]
        projected_end = max(center_rate * 0.08, 0.001)
        visible_values.append(projected_end)
        log_y_min = math.floor(min(log10_safe(value) for value in visible_values))
        log_y_max = math.ceil(max(log10_safe(value) for value in visible_values))
    else:
        center_log = log10_safe(center_rate)
        log_span = float(plot_config["logSpanDecades"])
        log_y_min = center_log - log_span / 2.0
        log_y_max = center_log + log_span / 2.0

    event_lines = []
    event_ranges: list[tuple[int, int, str]] = []
    active_event = ""
    active_start: int | None = None
    for index, row in enumerate(rows):
        event = row.get("Synthetic.EventType", "")
        event = "" if event == "normal" else event
        if event != active_event:
            if active_event and active_start is not None:
                event_ranges.append((active_start, index - 1, active_event))
            active_event = event
            active_start = index if event else None
    if active_event and active_start is not None:
        event_ranges.append((active_start, len(rows) - 1, active_event))

    if show_synthetic_events:
        for start_index, end_index, event in event_ranges:
            if end_index < x_min or start_index > x_max:
                continue
            clipped_start = max(float(start_index), x_min)
            clipped_end = min(float(end_index), x_max)
            x1 = plot_left + ((clipped_start - x_min) / max(x_max - x_min, 1e-9)) * plot_width
            x2 = plot_left + ((clipped_end - x_min) / max(x_max - x_min, 1e-9)) * plot_width
            width_attr = max(x2 - x1, 2.0)
            event_lines.append(
                f'<rect x="{x1:.2f}" y="{plot_top}" width="{width_attr:.2f}" height="{plot_height}" '
                f'fill="{guide_config["syntheticEventColor"]}" opacity="0.12" />'
            )
            if width_attr >= 35:
                label = event.replace("_", " ").replace("&", "&amp;")
                event_lines.append(
                    f'<text x="{x1 + 4:.2f}" y="{plot_top + 16}" font-family="Arial" font-size="10" '
                    f'fill="#555">{label}</text>'
                )

    origin_lines = []
    origin_dates = sorted({item["date"] for item in profile.get("fitOriginCandidates", [])})
    row_dates = [parse_date(row["Date"]).date().isoformat() for row in rows]
    arps_origin_index = oil[0][0] if oil else 0
    for origin in origin_dates:
        if origin in row_dates:
            origin_index = row_dates.index(origin)
            arps_origin_index = origin_index
            if origin_index < x_min or origin_index > x_max:
                continue
            x = plot_left + ((origin_index - x_min) / max(x_max - x_min, 1e-9)) * plot_width
            origin_lines.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_top + plot_height}" '
                f'stroke="{guide_config["forecastOriginColor"]}" stroke-width="2" stroke-dasharray="8 5" opacity="0.8" />'
            )

    visual_terminal_rate = value_from_log(log_y_min)
    oil_arps_fit, oil_arps_path = arps_fit_svg_path(
        oil, arps_origin_index, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height, visual_terminal_rate
    )
    gor_fit = fit_ratio_profile(gas, oil, arps_origin_index, "GOR")
    wor_fit = fit_ratio_profile(water, oil, arps_origin_index, "WOR")
    gas_ratio_points = ratio_derived_rate_path(oil_arps_fit, gor_fit, arps_origin_index, visual_terminal_rate)
    water_ratio_points = ratio_derived_rate_path(oil_arps_fit, wor_fit, arps_origin_index, visual_terminal_rate)
    gas_ratio_path = path_for(gas_ratio_points, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
    water_ratio_path = path_for(water_ratio_points, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
    effective_date = parse_date(rows[0]["Date"]) + timedelta(days=arps_origin_index) if rows else datetime(2024, 1, 1)
    oil_forecast_points = oil_arps_fit.get("points", []) if oil_arps_fit else []
    volume_box = cumulative_volume_box(
        oil,
        gas,
        water,
        oil_forecast_points,
        gas_ratio_points,
        water_ratio_points,
        center_index,
        plot_left + 10,
        plot_top + 10,
    )
    equation_box = arps_equation_box(effective_date, oil_arps_fit, gor_fit, wor_fit, plot_left + plot_width - 530, plot_top + 10)

    fit_labels = []
    if oil_arps_fit:
        fit_labels.append(
            f'Oil Arps: Di={oil_arps_fit["nominalDiAnnual"]:.2f}/yr b={oil_arps_fit["bFactor"]:.1f}'
        )
    if gor_fit:
        fit_labels.append(f'Gas = oil forecast * {gor_fit["stageCount"]}-stage GOR')
    if wor_fit:
        fit_labels.append(f'Water = oil forecast * {wor_fit["stageCount"]}-stage WOR')
    arps_fit_label = " | ".join(fit_labels)

    center_marker = ""
    if last_oil is not None:
        center = point_xy(last_oil[0], last_oil[1], x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
        if center:
            cx, cy = center
            center_marker = (
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="6" fill="{guide_config["centerMarkerColor"]}" stroke="#fff" stroke-width="2" />'
                f'<text x="{cx + 10:.2f}" y="{cy - 10:.2f}" font-family="Arial" font-size="12" font-weight="700" fill="#000">Time 0 / forecast start</text>'
            )

    title = well.replace("&", "&amp;")
    interp = dominant_interpretation(profile)
    reasons = recommendation.get("reasons", [])[:3]
    reason_text = " | ".join(reasons).replace("&", "&amp;")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="40" y="34" font-family="Arial" font-size="22" font-weight="700">{title}</text>
  <text x="40" y="58" font-family="Arial" font-size="13" fill="#333">QC: {recommendation["qc"]} | Method: {recommendation["recommendedMethod"]} | Pressure: {interp}</text>
  <text x="40" y="78" font-family="Arial" font-size="12" fill="#555">{reason_text}</text>
  <rect x="{plot_left}" y="{plot_top}" width="{plot_width}" height="{plot_height}" fill="#fbfbfb" stroke="#111"/>
  {log_grid(log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}
  {x_grid_calendar(x_min, x_max, parse_date(rows[0]["Date"]), center_index, plot_left, plot_width, plot_top, plot_height) if full_data_view and rows else x_grid(x_min, x_max, center_index, plot_left, plot_width, plot_top, plot_height)}
  {''.join(event_lines)}
  {''.join(origin_lines)}
  {volume_box}
  {equation_box}
  {center_marker}
  <path d="{path_for(oil, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["oil"]["color"]}" stroke-width="2.2"/>
  <path d="{oil_arps_path}" fill="none" stroke="{series_config["oil"]["color"]}" stroke-width="2.4" stroke-dasharray="10 6" opacity="0.9"/>
  <path d="{path_for(gas, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["gas"]["color"]}" stroke-width="1.8"/>
  <path d="{gas_ratio_path}" fill="none" stroke="{series_config["gas"]["color"]}" stroke-width="2.2" stroke-dasharray="10 6" opacity="0.85"/>
  <path d="{path_for(water, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["water"]["color"]}" stroke-width="1.6"/>
  <path d="{water_ratio_path}" fill="none" stroke="{series_config["water"]["color"]}" stroke-width="2.0" stroke-dasharray="10 6" opacity="0.85"/>
  <path d="{path_for(casing, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["casingPressure"]["color"]}" stroke-width="1.4" opacity="0.75"/>
  <path d="{path_for(tubing, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["tubingPressure"]["color"]}" stroke-width="1.4" opacity="0.75"/>
  <path d="{path_for(pip, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["pumpIntakePressure"]["color"]}" stroke-width="1.4" opacity="0.75"/>
  <text x="70" y="540" font-family="Arial" font-size="13" fill="{series_config["oil"]["color"]}">{series_config["oil"]["label"]}</text>
  <text x="120" y="540" font-family="Arial" font-size="13" fill="{series_config["gas"]["color"]}">{series_config["gas"]["label"]}</text>
  <text x="170" y="540" font-family="Arial" font-size="13" fill="{series_config["water"]["color"]}">{series_config["water"]["label"]}</text>
  <text x="230" y="540" font-family="Arial" font-size="13" fill="{series_config["casingPressure"]["color"]}">{series_config["casingPressure"]["label"]}</text>
  <text x="310" y="540" font-family="Arial" font-size="13" fill="{series_config["tubingPressure"]["color"]}">{series_config["tubingPressure"]["label"]}</text>
  <text x="390" y="540" font-family="Arial" font-size="13" fill="{series_config["pumpIntakePressure"]["color"]}">{series_config["pumpIntakePressure"]["label"]}</text>
  <text x="70" y="565" font-family="Arial" font-size="12" fill="#666">Dashed green = oil Arps hyp-to-exp; dashed red/blue = oil forecast multiplied by fitted GOR/WOR ratio profiles.</text>
  <text x="70" y="590" font-family="Arial" font-size="12" fill="#666">{arps_fit_label}</text>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate experimental SVG sample plots organized by forecast profile. "
            "Use the forecasting area PNG reference image as the canonical final plot style."
        )
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()

    input_path = Path(args.input)
    profile_path = Path(args.profile)
    output_root = Path(args.output)
    config = load_chart_config(Path(args.config))
    rows_by_well = load_rows(input_path)
    profiles = load_profile(profile_path)
    recommendations = load_recommendations(profile_path)

    count = 0
    for well, rows in sorted(rows_by_well.items()):
        profile = profiles.get(well)
        recommendation = recommendations.get(well)
        if not profile or not recommendation:
            continue
        group = f"qc_{recommendation['qc']}/{dominant_interpretation(profile)}"
        output_dir = output_root / group
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{slug(well)}.svg"
        output_path.write_text(render_svg(well, rows, profile, recommendation, config=config), encoding="utf-8")
        count += 1

    print(f"Wrote {count} SVG plots under {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
