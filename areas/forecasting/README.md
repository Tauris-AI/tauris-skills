# Forecasting

Auto-forecasting workflow support for production and pressure datasets.

## Included Assets

- MCP server: `mcp-servers/forecasting-mcp`
- Skill: `skills/auto-forecasting`
- Chart reference: `assets/engineering_log_decline_plot_reference.png`

## Scope

Use this area to profile multi-well production datasets, evaluate available pressure signals, choose eligible forecast method families, identify candidate forecast origins, and produce forecast QC guidance before running deeper Arps or hybrid model fitting.

The current workflow is method-selection and QC oriented. It assumes many real datasets will not contain enough reservoir, PVT, completion, pressure-transient, or operating-detail inputs for full reservoir-engineering calculations. Detailed Arps fitting implementations remain in `OilGas/ArpsForecasting` until they are refactored behind a stable engine contract.

When this area exports an ARIES database, it should not write Access directly.
Build normalized ARIES table payloads and call the shared writer in
`../aries/mcp-servers/aries-mcp/aries_access_writer.py`.

## Chart View

Use `assets/engineering_log_decline_plot_reference.png` as the canonical visual target for final forecast plots. It shows the expected engineering-style log plot, colored phase/pressure curves, grid density, and history/forecast orientation. Generated SVG plots are scaffolding only until a production chart renderer is built.
