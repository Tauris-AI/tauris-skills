#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
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
            stroke = "#111" if major else "#999"
            opacity = "0.7" if major else "0.28"
            width_attr = "1.1" if major else "0.7"
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
    half_window = max(forecast_days, min(center_index, forecast_days))
    x_min = max(0.0, center_index - half_window)
    x_max = center_index + half_window
    center_log = log10_safe(center_rate)
    log_span = float(plot_config["logSpanDecades"])
    log_y_min = center_log - log_span / 2.0
    log_y_max = center_log + log_span / 2.0

    event_lines = []
    for index, row in enumerate(rows):
        event = row.get("Synthetic.EventType", "")
        if event and event != "normal":
            if index < x_min or index > x_max:
                continue
            x = plot_left + ((index - x_min) / max(x_max - x_min, 1e-9)) * plot_width
            event_lines.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_top + plot_height}" '
                f'stroke="{guide_config["syntheticEventColor"]}" stroke-width="1" stroke-dasharray="4 5" opacity="0.45" />'
            )

    origin_lines = []
    fit_guides = []
    origin_dates = {item["date"] for item in profile.get("fitOriginCandidates", [])}
    row_dates = [parse_date(row["Date"]).date().isoformat() for row in rows]
    for origin in origin_dates:
        if origin in row_dates:
            origin_index = row_dates.index(origin)
            if origin_index < x_min or origin_index > x_max:
                continue
            x = plot_left + ((origin_index - x_min) / max(x_max - x_min, 1e-9)) * plot_width
            origin_lines.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_top + plot_height}" '
                f'stroke="{guide_config["forecastOriginColor"]}" stroke-width="2" stroke-dasharray="8 5" opacity="0.8" />'
            )
            origin_oil = parse_float(rows[origin_index].get("OIL - Resolver"))
            if origin_oil is not None and last_oil is not None:
                p1 = point_xy(origin_index, origin_oil, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
                p2 = point_xy(last_oil[0], last_oil[1], x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
                if p1 and p2:
                    x1, y1 = p1
                    x2, y2 = p2
                    fit_guides.append(
                        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                        f'stroke="{guide_config["fitGuideColor"]}" stroke-width="1.5" stroke-dasharray="3 4" opacity="0.55" />'
                    )

    projection_guide = ""
    if last_oil is not None:
        p1 = point_xy(last_oil[0], last_oil[1], x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
        projected_end = max(last_oil[1] * 0.55, 0.0)
        p2 = point_xy(last_oil[0] + forecast_days, projected_end, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)
        if p1 and p2:
            x1, y1 = p1
            x2, y2 = p2
            projection_guide = (
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{guide_config["projectionGuideColor"]}" stroke-width="3" opacity="0.85" />'
            )

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
  {x_grid(x_min, x_max, center_index, plot_left, plot_width, plot_top, plot_height)}
  {''.join(event_lines)}
  {''.join(origin_lines)}
  {''.join(fit_guides)}
  {projection_guide}
  {center_marker}
  <path d="{path_for(oil, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["oil"]["color"]}" stroke-width="2.2"/>
  <path d="{path_for(gas, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["gas"]["color"]}" stroke-width="1.8"/>
  <path d="{path_for(water, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["water"]["color"]}" stroke-width="1.6"/>
  <path d="{path_for(casing, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["casingPressure"]["color"]}" stroke-width="1.4" opacity="0.75"/>
  <path d="{path_for(tubing, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["tubingPressure"]["color"]}" stroke-width="1.4" opacity="0.75"/>
  <path d="{path_for(pip, x_min, x_max, log_y_min, log_y_max, plot_left, plot_width, plot_top, plot_height)}" fill="none" stroke="{series_config["pumpIntakePressure"]["color"]}" stroke-width="1.4" opacity="0.75"/>
  <text x="70" y="540" font-family="Arial" font-size="13" fill="{series_config["oil"]["color"]}">{series_config["oil"]["label"]}</text>
  <text x="120" y="540" font-family="Arial" font-size="13" fill="{series_config["gas"]["color"]}">{series_config["gas"]["label"]}</text>
  <text x="170" y="540" font-family="Arial" font-size="13" fill="{series_config["water"]["color"]}">{series_config["water"]["label"]}</text>
  <text x="230" y="540" font-family="Arial" font-size="13" fill="{series_config["casingPressure"]["color"]}">{series_config["casingPressure"]["label"]}</text>
  <text x="310" y="540" font-family="Arial" font-size="13" fill="{series_config["tubingPressure"]["color"]}">{series_config["tubingPressure"]["label"]}</text>
  <text x="390" y="540" font-family="Arial" font-size="13" fill="{series_config["pumpIntakePressure"]["color"]}">{series_config["pumpIntakePressure"]["label"]}</text>
  <text x="70" y="565" font-family="Arial" font-size="12" fill="#666">Dashed gray = synthetic event, purple = candidate fit origin, thin dashed black = straight fit guide, thick black = straight projection guide</text>
  <text x="70" y="590" font-family="Arial" font-size="12" fill="#666">History can be event-disrupted; forecast/projection guides are drawn as straight lines for portability review.</text>
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
