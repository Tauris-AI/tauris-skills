#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path


FIELDNAMES = [
    "Entity Name",
    "Asset Name",
    "Date",
    "OIL - Resolver",
    "GAS - Resolver",
    "WATER - Resolver",
    "Oil - NRI - Resolver",
    "Gas - NRI - Resolver",
    "Water - NRI - Resolver",
    "Well.Pressure.PumpIntake - Resolver",
    "Well.Pressure.Casing - Resolver",
    "Well.Pressure.Tubing - Resolver",
    "Well.Hours.Flowed - Resolver",
    "Well.Choke - Resolver",
    "Synthetic.EventType",
    "Synthetic.EventNote",
]


def arps_rate(qi: float, di: float, b: float, day: int) -> float:
    return qi / ((1.0 + b * di * day) ** (1.0 / b))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_row(
    well: str,
    start: date,
    day: int,
    oil: float,
    gor: float,
    water_cut: float,
    pip: float,
    casing: float,
    tubing: float,
    hours: float,
    choke: float,
    event_type: str = "normal",
    event_note: str = "",
) -> dict[str, object]:
    gas = oil * gor
    water = oil * water_cut / max(1.0 - water_cut, 0.05)
    uptime = clamp(hours / 24.0, 0.0, 1.0)
    oil *= uptime
    gas *= uptime
    water *= uptime
    return {
        "Entity Name": well,
        "Asset Name": "Synthetic Unconventional Oil",
        "Date": (start + timedelta(days=day)).strftime("%m/%d/%Y"),
        "OIL - Resolver": round(oil, 3),
        "GAS - Resolver": round(gas, 3),
        "WATER - Resolver": round(water, 3),
        "Oil - NRI - Resolver": round(oil * 0.018, 6),
        "Gas - NRI - Resolver": round(gas * 0.018, 6),
        "Water - NRI - Resolver": round(water * 0.018, 6),
        "Well.Pressure.PumpIntake - Resolver": round(pip, 2) if pip >= 0 else "",
        "Well.Pressure.Casing - Resolver": round(casing, 2) if casing >= 0 else "",
        "Well.Pressure.Tubing - Resolver": round(tubing, 2) if tubing >= 0 else "",
        "Well.Hours.Flowed - Resolver": round(hours, 2),
        "Well.Choke - Resolver": round(choke, 2) if choke >= 0 else "",
        "Synthetic.EventType": event_type,
        "Synthetic.EventNote": event_note,
    }


def generate_well(well: str, days: int, scenario: str, seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    start = date(2024, 1, 1)
    qi = rng.uniform(850, 1250)
    di = rng.uniform(0.0045, 0.007)
    b = rng.uniform(0.85, 1.35)
    base_gor = rng.uniform(1.2, 2.2)
    rows: list[dict[str, object]] = []

    for day in range(days):
        oil = arps_rate(qi, di, b, day)
        gor = base_gor * (1.0 + 0.0009 * day)
        water_cut = clamp(0.18 + 0.00035 * day, 0.12, 0.58)
        pip = 1850 - day * 2.2
        casing = 2600 - day * 2.9
        tubing = 1650 - day * 2.1
        hours = 24.0
        choke = 36.0
        event_type = "normal"
        event_note = ""

        if scenario == "base_depletion":
            pass
        elif scenario == "pump_swap_month_3_4":
            if 75 <= day < 95:
                event_type = "pump_swap_transition"
                event_note = "Pump swap transition; test fit windows before and after event."
                hours = 16 + (day - 75) * 0.35
                oil *= 0.78 + (day - 75) * 0.012
                pip += 180 - (day - 75) * 7
            elif day >= 95:
                event_type = "post_pump_swap"
                event_note = "Improved drawdown after pump swap."
                oil *= 1.28
                gor *= 1.08
                pip -= 260
                tubing -= 130
        elif scenario == "pump_failure":
            if day >= 210:
                event_type = "pump_failure_or_lift_issue"
                event_note = "Rate loss with flat/rising pressure and lower flowing hours."
                oil *= 0.52
                gor *= 0.9
                pip += 220
                casing += 160
                tubing += 80
                hours = 11.5
        elif scenario == "shutin_restart":
            if 160 <= day < 182:
                event_type = "shutin"
                event_note = "Shut-in interval."
                oil = 0
                gor = 0
                water_cut = 0
                hours = 0
                pip += 420
                casing += 360
                tubing += 260
            elif 182 <= day < 230:
                event_type = "restart_cleanup"
                event_note = "Restart cleanup period; avoid using as stable decline."
                oil *= 1.45 * math.exp(-0.008 * (day - 182))
                water_cut = clamp(water_cut + 0.18 * math.exp(-0.025 * (day - 182)), 0.0, 0.75)
                pip -= 170
        elif scenario == "frac_hit_or_offset_completion":
            if 250 <= day < 285:
                event_type = "frac_hit_response"
                event_note = "Offset completion response with pressure/water/rate disturbance."
                oil *= 1.45
                water_cut = clamp(water_cut + 0.22, 0.0, 0.8)
                pip += 350
                casing += 520
                tubing += 220
            elif day >= 285:
                event_type = "post_frac_hit"
                event_note = "Post-disturbance regime."
                oil *= 1.12
                water_cut = clamp(water_cut + 0.08, 0.0, 0.7)
        elif scenario == "choke_constraint":
            if day >= 140:
                event_type = "choke_constraint"
                event_note = "Choke reduced; rate drop is not pure reservoir decline."
                choke = 18.0
                oil *= 0.58
                pip += 260
                casing += 180
                tubing += 120
        elif scenario == "facility_downtime":
            if day % 37 in {0, 1, 2, 3} or 300 <= day < 320:
                event_type = "facility_downtime"
                event_note = "Intermittent facility downtime."
                hours = 6.0 if day % 37 in {0, 1, 2, 3} else 3.0
        elif scenario == "gor_rise":
            if day >= 240:
                event_type = "gas_ratio_increase"
                event_note = "Associated gas ratio rises faster than oil trend."
                gor *= 1.0 + 0.006 * (day - 240)
                casing -= 0.8 * (day - 240)
        elif scenario == "water_loadup":
            if day >= 180:
                event_type = "water_loadup_or_fluid_level"
                event_note = "Water cut rises and oil underperforms."
                water_cut = clamp(water_cut + 0.0025 * (day - 180), 0.0, 0.85)
                oil *= max(0.35, 1.0 - 0.002 * (day - 180))
                pip += 1.2 * (day - 180)
        elif scenario == "missing_pressure":
            pip = casing = tubing = -1
            if day % 29 == 0:
                event_type = "minor_operational_noise"
                event_note = "No pressure data available."
                hours = 18
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        oil *= rng.uniform(0.965, 1.035)
        pip += rng.uniform(-18, 18) if pip >= 0 else 0
        casing += rng.uniform(-25, 25) if casing >= 0 else 0
        tubing += rng.uniform(-16, 16) if tubing >= 0 else 0
        rows.append(build_row(well, start, day, oil, gor, water_cut, pip, casing, tubing, hours, choke, event_type, event_note))

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic unconventional oil forecasting scenarios.")
    parser.add_argument(
        "--output",
        default="areas/forecasting/mcp-servers/forecasting-mcp/data/input/synthetic_unconventional_daily.csv",
    )
    args = parser.parse_args()

    scenarios = [
        ("SYNTH BASE DEPLETION 01H", 365, "base_depletion"),
        ("SYNTH PUMP SWAP MONTH 3 02H", 420, "pump_swap_month_3_4"),
        ("SYNTH PUMP FAILURE 03H", 450, "pump_failure"),
        ("SYNTH SHUTIN RESTART 04H", 365, "shutin_restart"),
        ("SYNTH FRAC HIT 05H", 540, "frac_hit_or_offset_completion"),
        ("SYNTH CHOKE CONSTRAINT 06H", 365, "choke_constraint"),
        ("SYNTH FACILITY DOWNTIME 07H", 420, "facility_downtime"),
        ("SYNTH GOR RISE 08H", 720, "gor_rise"),
        ("SYNTH WATER LOADUP 09H", 540, "water_loadup"),
        ("SYNTH MISSING PRESSURE 10H", 365, "missing_pressure"),
    ]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for index, (well, days, scenario) in enumerate(scenarios, start=1):
        rows.extend(generate_well(well, days, scenario, seed=1729 + index))

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows for {len(scenarios)} wells to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
