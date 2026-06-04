---
name: auto-forecasting
description: Use for production auto-forecasting workflow design and review: profiling multi-well production/pressure datasets, selecting eligible decline or hybrid method families, assigning QC confidence, and routing wells for human forecast review. Do not use for PHDWin extraction or ARIES table editing.
---

# Auto Forecasting

Use this skill when the task is to decide how production data should be forecasted before or after running decline fitting.

This is a limited-data production forecasting skill, not a full reservoir-engineering simulator. In normal Tauris workflows, required reservoir, PVT, completion, pressure-transient, and operating details may be incomplete or unavailable. State those limits explicitly and use them as QC reasons.

## Workflow

1. Profile the dataset before fitting:
   - well/date columns
   - daily, weekly, monthly, sparse, or unknown cadence
   - usable oil, gas, and water signals
   - usable casing pressure, flowing tubing pressure, and pump inlet/intake pressure
   - candidate forecast origin dates, including first production and possible post-recompletion or post-stimulation starts
2. Classify method eligibility per well:
   - daily production with usable pressure can run pressure-aware residual diagnostics
   - daily production without pressure should use decline methods plus fit-window scanning
   - monthly production should prefer simpler reserves-style decline fitting
   - short or sparse histories should be yellow/red QC and routed to human review
3. Run candidate methods only after eligibility is clear.
4. Test fit-origin candidates before selecting a champion curve.
5. Score candidates with both numeric fit and engineering guardrails.
6. Return a recommendation with alternatives, QC status, and reasons.

## Forecast Origin Guidance

Do not assume day 1 or month 1 is the correct forecast origin. A recompletion, stimulation, artificial-lift change, constraint removal, or cleanup period can make full-history fitting misleading.

When origin candidates exist:

- fit from first positive production as a baseline
- fit from each separated sustained uplift as a candidate
- use pressure step changes as context for fit-window selection
- mark QC yellow when the selected origin materially changes EUR or forecast shape
- ask for human review when origin choice dominates the forecast

## Pressure Guidance

Use pressure as context first:

- rate down and pressure down: decline fit may be depletion-driven
- rate down and pressure flat/up: possible constraint, downtime, lift, choke, facility, or data issue
- rate up and pressure down: possible drawdown change or cleanup period
- volatile rate and volatile pressure: operationally unstable, human review likely needed

Do not let pressure-aware models run when pressure coverage is sparse, stale, or poorly aligned with production dates.

Pressure should influence projection choice this way:

- classify whether rate decline is depletion-supported or potentially operational
- choose fit windows and candidate forecast origins
- decide whether pressure-aware residual methods are eligible
- raise or lower QC confidence
- explain why a human should review a well

Do not use pressure to force a physics-based projection when bottomhole pressure, PVT, completion, reservoir, and operating details are unavailable.

## Limited-Data Guardrail

When reservoir-engineering inputs are missing, do not invent:

- drainage area
- permeability
- skin
- fracture geometry
- flowing bottomhole pressure
- PVT properties
- material balance
- pressure-transient interpretation

Use production and surface/downhole pressure signals to write better method logic, fit-window choices, and QC explanations. Do not present the result as a physics-complete reservoir calculation.

## Decline Convention Export

Keep internal fitting math separate from commercial app entry values.

When exporting Arps parameters to ARIES, ComboCurve, PHDWin, Mosaic, or similar tools:

- pin the time basis to years before converting decline values
- do not export nominal `Di` directly when the app expects effective annual decline
- convert initial nominal Arps decline to effective secant annual decline:
  - exponential: `1 - exp(-Di_annual)`
  - hyperbolic: `1 - (1 + b * Di_annual)^(-1 / b)`
- convert terminal nominal exponential `Dmin` to effective annual exponential decline:
  - `1 - exp(-Dmin_annual)`

Use `convert_decline_convention` in the forecasting MCP to show the numbers an engineer should type into commercial software.

## MCP Tool

For CSV profiling and method recommendation, use:

```text
areas/forecasting/mcp-servers/forecasting-mcp/forecasting_mcp.py
```

Primary tool:

```text
profile_and_recommend(csv_path)
```

Use `pressureProjectionDiagnostics` and `fitOriginCandidates` from its output to decide which ArpsForecasting methods and fit windows should be applied later.

Convention tool:

```text
convert_decline_convention(nominal_di, b_factor, terminal_dmin, input_time_unit)
```

## Chart Reference

Use `areas/forecasting/assets/engineering_log_decline_plot_reference.png` as the canonical final-plot style. Do not treat generated SVG samples as authoritative. A production chart should match the reference image's engineering log plot behavior, colored series conventions, dense grid, and history/forecast orientation.
