#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("areas/forecasting/mcp-servers/forecasting-mcp/data/input/synthetic_unconventional_daily.csv")
DEFAULT_PROFILE = Path("areas/forecasting/mcp-servers/forecasting-mcp/data/output/synthetic_unconventional_daily_profile.json")
DEFAULT_OUTPUT = Path("areas/forecasting/mcp-servers/forecasting-mcp/data/output/plots")


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


def series_points(rows: list[dict[str, Any]], column: str) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    for index, row in enumerate(rows):
        value = parse_float(row.get(column))
        if value is not None and value >= 0:
            points.append((index, value))
    return points


def path_for(points: list[tuple[float, float]], x_scale: float, y_min: float, y_max: float, top: int, height: int) -> str:
    if not points:
        return ""
    denom = max(y_max - y_min, 1e-9)
    commands = []
    for index, value in points:
        x = 70 + index * x_scale
        y = top + height - ((value - y_min) / denom) * height
        commands.append(("M" if not commands else "L") + f"{x:.2f},{y:.2f}")
    return " ".join(commands)


def point_xy(index: float, value: float, x_scale: float, y_min: float, y_max: float, top: int, height: int) -> tuple[float, float]:
    denom = max(y_max - y_min, 1e-9)
    x = 70 + index * x_scale
    y = top + height - ((value - y_min) / denom) * height
    return x, y


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


def render_svg(well: str, rows: list[dict[str, Any]], profile: dict[str, Any], recommendation: dict[str, Any]) -> str:
    width = 1120
    height = 620
    plot_top = 90
    plot_height = 420
    plot_width = 980
    forecast_days = min(180, max(60, len(rows) // 3))
    total_points = len(rows) + forecast_days
    x_scale = plot_width / max(total_points - 1, 1)

    oil = series_points(rows, "OIL - Resolver")
    gas = series_points(rows, "GAS - Resolver")
    water = series_points(rows, "WATER - Resolver")
    casing = series_points(rows, "Well.Pressure.Casing - Resolver")
    tubing = series_points(rows, "Well.Pressure.Tubing - Resolver")
    pip = series_points(rows, "Well.Pressure.PumpIntake - Resolver")

    rate_values = [value for _, value in oil + gas + water]
    pressure_values = [value for _, value in casing + tubing + pip]
    rate_min, rate_max = 0, max(rate_values or [1])
    pressure_min, pressure_max = 0, max(pressure_values or [1])
    last_oil = oil[-1] if oil else None

    event_lines = []
    for index, row in enumerate(rows):
        event = row.get("Synthetic.EventType", "")
        if event and event != "normal":
            x = 70 + index * x_scale
            event_lines.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_top + plot_height}" '
                'stroke="#888" stroke-width="1" stroke-dasharray="4 5" opacity="0.45" />'
            )

    origin_lines = []
    fit_guides = []
    origin_dates = {item["date"] for item in profile.get("fitOriginCandidates", [])}
    row_dates = [parse_date(row["Date"]).date().isoformat() for row in rows]
    for origin in origin_dates:
        if origin in row_dates:
            origin_index = row_dates.index(origin)
            x = 70 + origin_index * x_scale
            origin_lines.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_top + plot_height}" '
                'stroke="#8a2be2" stroke-width="2" stroke-dasharray="8 5" opacity="0.8" />'
            )
            origin_oil = parse_float(rows[origin_index].get("OIL - Resolver"))
            if origin_oil is not None and last_oil is not None:
                x1, y1 = point_xy(origin_index, origin_oil, x_scale, rate_min, rate_max, plot_top, plot_height)
                x2, y2 = point_xy(last_oil[0], last_oil[1], x_scale, rate_min, rate_max, plot_top, plot_height)
                fit_guides.append(
                    f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                    'stroke="#111" stroke-width="1.5" stroke-dasharray="3 4" opacity="0.55" />'
                )

    projection_guide = ""
    if last_oil is not None:
        x1, y1 = point_xy(last_oil[0], last_oil[1], x_scale, rate_min, rate_max, plot_top, plot_height)
        projected_end = max(last_oil[1] * 0.55, 0.0)
        x2, y2 = point_xy(len(rows) + forecast_days - 1, projected_end, x_scale, rate_min, rate_max, plot_top, plot_height)
        projection_guide = (
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            'stroke="#000" stroke-width="3" opacity="0.85" />'
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
  <rect x="70" y="{plot_top}" width="{plot_width}" height="{plot_height}" fill="#fbfbfb" stroke="#ddd"/>
  {''.join(event_lines)}
  {''.join(origin_lines)}
  {''.join(fit_guides)}
  {projection_guide}
  <path d="{path_for(oil, x_scale, rate_min, rate_max, plot_top, plot_height)}" fill="none" stroke="#1874d1" stroke-width="2.2"/>
  <path d="{path_for(gas, x_scale, rate_min, rate_max, plot_top, plot_height)}" fill="none" stroke="#2d9d51" stroke-width="1.8"/>
  <path d="{path_for(water, x_scale, rate_min, rate_max, plot_top, plot_height)}" fill="none" stroke="#a56a20" stroke-width="1.6"/>
  <path d="{path_for(casing, x_scale, pressure_min, pressure_max, plot_top, plot_height)}" fill="none" stroke="#d14d32" stroke-width="1.4" opacity="0.75"/>
  <path d="{path_for(tubing, x_scale, pressure_min, pressure_max, plot_top, plot_height)}" fill="none" stroke="#7b5bd6" stroke-width="1.4" opacity="0.75"/>
  <path d="{path_for(pip, x_scale, pressure_min, pressure_max, plot_top, plot_height)}" fill="none" stroke="#5f7682" stroke-width="1.4" opacity="0.75"/>
  <text x="70" y="540" font-family="Arial" font-size="13" fill="#1874d1">Oil</text>
  <text x="120" y="540" font-family="Arial" font-size="13" fill="#2d9d51">Gas</text>
  <text x="170" y="540" font-family="Arial" font-size="13" fill="#a56a20">Water</text>
  <text x="230" y="540" font-family="Arial" font-size="13" fill="#d14d32">Casing P</text>
  <text x="310" y="540" font-family="Arial" font-size="13" fill="#7b5bd6">Tubing P</text>
  <text x="390" y="540" font-family="Arial" font-size="13" fill="#5f7682">Pump Intake P</text>
  <text x="70" y="565" font-family="Arial" font-size="12" fill="#666">Dashed gray = synthetic event, purple = candidate fit origin, thin dashed black = straight fit guide, thick black = straight projection guide</text>
  <text x="70" y="590" font-family="Arial" font-size="12" fill="#666">History can be event-disrupted; forecast/projection guides are drawn as straight lines for portability review.</text>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SVG sample plots organized by forecast profile.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    input_path = Path(args.input)
    profile_path = Path(args.profile)
    output_root = Path(args.output)
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
        output_path.write_text(render_svg(well, rows, profile, recommendation), encoding="utf-8")
        count += 1

    print(f"Wrote {count} SVG plots under {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
