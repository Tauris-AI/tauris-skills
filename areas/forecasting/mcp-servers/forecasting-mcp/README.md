# Forecasting MCP

Python MCP server for Claude Cowork to profile multi-well production and pressure CSVs before decline fitting.

## Purpose

This first version does not generate final forecasts. It helps decide which forecast method families are appropriate per well based on available production cadence, production coverage, and pressure signals.

## Tools

- `profile_csv`: infer well/date/production/pressure columns and profile each well.
- `recommend_methods`: recommend forecast methods for one well profile.
- `profile_and_recommend`: run profiling and method recommendation in one call.
- `run_monthly_production_dca_batch`: default monthly production upload workflow. Runs profiling, local monthly DCA candidates, Green/Yellow/Red QC routing, one PNG per well, summary CSV/JSON outputs, and analog screening for early-stage wells.
- `convert_decline_convention`: convert internal nominal decline values to commercial app entry values.
- `validate_industry_alignment`: check whether a well profile/recommendation is directionally aligned with limited-data petroleum engineering DCA practice.

Profiles include `fitOriginCandidates` so Cowork can detect cases where the forecast should start after first production, a recompletion, a stimulation, cleanup, or another operating change instead of blindly fitting the full history.

Profiles also include `pressureProjectionDiagnostics`, which compares production trends with usable pressure trends. Use those diagnostics to decide whether a projection is depletion-supported, possibly constrained/operational, a drawdown/recompletion response, hidden depletion risk, or unstable.

## Cowork Config

Merge `cowork_config.example.json` into the Cowork developer MCP config.

## Pressure Signals

The profiler recognizes casing pressure, flowing tubing pressure, tubing pressure, pump inlet pressure, and pump intake pressure aliases. Pressure data is used for method eligibility, fit-window guidance, and QC, not as an automatic replacement for engineering review.

## Decline Convention Export

The conversion tool pins time to years, converts initial nominal Arps decline to effective secant annual decline, and converts terminal nominal exponential decline to effective annual exponential decline. Use these output values for ARIES, ComboCurve, PHDWin, Mosaic, and similar forecast-entry screens that expect effective annual decline conventions.

## Chart Reference

Use `../../assets/engineering_log_decline_plot_reference.png` as the final plot reference. The SVG generator is only a local scaffold; it is not the target chart implementation.

The maintained chart object/design contract is archived in:

```text
chart_object_designer.archive.md
```

Claude Code should read that archive before changing chart layout, axis behavior, QC folders, ratio display, pressure-context display, or bottom-panel content.

## Default Monthly Upload Workflow

When the user provides one monthly production CSV zip plus one well metadata CSV zip, Cowork should call:

```text
run_monthly_production_dca_batch(production_zip, wells_zip, output_dir?, chart_config?)
```

The default chart/batch configuration is `chart_config.default.json`. It controls chart layout, ratio colors and right-axis scaling, lifecycle thresholds, QC colors, forecast horizon, and future pressure-context styling.
