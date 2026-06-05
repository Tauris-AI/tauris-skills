# Forecast Chart Object Designer Archive

This archive documents the chart object used by the monthly production DCA batch workflow. Claude Code should read this file before changing chart behavior.

## Runtime Files

- Chart renderer and batch workflow: `monthly_production_dca_batch.py`
- Default chart configuration: `chart_config.default.json`
- MCP entry point and Cowork-facing tool wrapper: `forecasting_mcp.py`
- Default MCP tool for monthly uploads: `run_monthly_production_dca_batch`

## Chart Purpose

Create one engineering-review PNG per well from monthly production data. The chart is not a reservoir-simulation result. It is a limited-data DCA review artifact that shows:

- historical oil, gas, and water rates on the left-hand log axis
- selected forecast curves when a DCA fit is reliable enough to show
- supporting GOR/WOR or OGR/WGR ratios on the right-hand log axis
- the recent fit/scoring window as a light gray band
- Green/Yellow/Red QC routing
- selected methods, Arps/ratio parameters, and EUR summary

## Config Contract

Default settings live in `chart_config.default.json`.

Key sections:

- `plot`: canvas size, plot rectangle, print margin, and visualization clipping behavior
- `forecast`: forecast horizon, time step, terminal decline, and recent-fit QC thresholds
- `lifecycle`: early-stage threshold for minimum positive primary-product months
- `series`: oil/gas/water labels and left-axis colors
- `ratios`: GOR/WOR/WGR right-axis behavior and colors
- `pressure`: future pressure-context styling and notes
- `qcColors`: Green/Yellow/Red badge colors
- `legend`: right-side legend placement

When adding chart behavior, prefer adding a config key rather than hard-coding values in the renderer.

## Visual Layout

Canvas:

- default image size: `1120 x 700`
- default print margin: `30 px`, applied after rendering
- chart content remains on a white page

Plot:

- default plot rectangle: `(left=72, top=116, right=920, bottom=438)`
- left axis: production rate, log scale, vertical label `Rate (LH)`
- right axis: ratios, log scale, vertical label `Ratio (RH)`
- x axis: years from first production month

Legend:

- placed to the right of the plot, not inside the data panel
- production series are labeled with `(LH)`
- ratio series are labeled with `(RH)`
- do not show separate `history` and `forecast` legend rows for regular forecast charts
- no-fit early-stage charts may show `history point` to explain marker-only plots

## Series Colors

Defaults:

- Oil: green `#288246`
- Gas: red `#be4137`
- Water: blue `#2d69b4`
- GOR: magenta/pink `#dc379b`
- WOR/WGR: teal `#00918c`

Pressure placeholders:

- Casing pressure: `#9a6a24`
- Tubing pressure: `#7d62b4`
- Pump intake pressure: `#607d80`

Pressure data is currently context/QC only. Do not use pressure as a standalone physics forecast without additional reservoir, PVT, completion, and operating details.

## Fit And QC Display

The top line uses:

- `Primary product`
- selected method
- `Recent fit error`, which is recent-window WAPE

The recent fit/scoring window is shaded light gray and labeled `recent fit`.

Bottom panels:

1. `Selected Methods`
   - compact primary, oil, gas, gas-ratio, and water-ratio method labels
   - compact RMSE/R2 snippets where space permits
2. `Arps / Ratio Params`
   - primary Arps equivalent parameters
   - `Qi`
   - `b`
   - effective annual `Di`
   - terminal nominal annual `Dmin`
   - recent fit month range
   - supporting ratio start/end values
3. `EUR Summary`
   - historical plus forecast oil
   - historical plus forecast gas
   - EUR in MBOE
   - EUR/ft when lateral length is available
   - basis note

## Forecast Drawing Rules

- Forecast calculations may use the full configured forecast horizon.
- Visualization must truncate forecast curves at the visible bottom axis; do not draw flat lines along the x-axis.
- Do not plot trailing zero or non-positive forecast values.
- Short-history or no-fit wells should plot history markers only and must not imply a DCA forecast.

## Lifecycle And QC Rules

Default lifecycle rule:

- fewer than `earlyStagePositivePrimaryMonths` positive primary-product months means `Still early stage`
- default threshold: `6`

Default recent-fit guardrails:

- Yellow if recent fit WAPE is above `yellowTailWapeThreshold`
- Red if recent fit WAPE is above `redTailWapeThreshold`
- Yellow if recent R2 is below `yellowIfTailR2Below`
- flag possible recent low-rate operational outliers using `recentOutlierLowRatio`

The current defaults intentionally route weak recent-fit wells to review instead of over-trusting a green label.

## Output Contract

The batch writes:

- `primary_product_charts/Green/*.png`
- `primary_product_charts/Yellow/*.png`
- `primary_product_charts/Red/*.png`
- `well_forecast_summary_green_yellow_red.csv`
- `well_forecast_summary_green_yellow_red.json`
- `best_method_selection_summary.csv`
- `analog_type_curve_screen.csv`
- `forecast_batch_run_summary.json`
- `RUN_SUMMARY.md`

The `ChartPath` field in the summary CSV must point to the QC subfolder.

## Future Pressure Context

The synthetic diagnostic workflow already uses these pressure/QC contexts:

- `no_pressure_diagnostic`
- `depletion_supported`
- `possible_constraint_or_operational_issue`
- `drawdown_or_recompletion_response`
- `hidden_depletion_risk`
- `operationally_unstable`

When pressure columns are available, show pressure as context and use `pressureProjectionDiagnostics` from `forecasting_mcp.py` to influence QC. Keep pressure-aware methods disabled when pressure coverage is sparse, stale, or misaligned with production dates.

## Update Checklist

When changing chart behavior:

1. Update `chart_config.default.json` for configurable behavior.
2. Update `monthly_production_dca_batch.py` only where renderer or batch logic needs implementation.
3. Keep `run_monthly_production_dca_batch` in `forecasting_mcp.py` as the Cowork-facing default workflow.
4. Rerun the batch on the current monthly test dataset.
5. Inspect one Green chart and one early-stage Red chart.
6. Confirm PNG counts match QC counts.
7. Update this archive when the chart object changes meaningfully.
