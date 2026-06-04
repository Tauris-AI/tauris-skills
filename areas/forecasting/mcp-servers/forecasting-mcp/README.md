# Forecasting MCP

Python MCP server for Claude Cowork to profile multi-well production and pressure CSVs before decline fitting.

## Purpose

This first version does not generate final forecasts. It helps decide which forecast method families are appropriate per well based on available production cadence, production coverage, and pressure signals.

## Tools

- `profile_csv`: infer well/date/production/pressure columns and profile each well.
- `recommend_methods`: recommend forecast methods for one well profile.
- `profile_and_recommend`: run profiling and method recommendation in one call.
- `convert_decline_convention`: convert internal nominal decline values to commercial app entry values.

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
