# Forecasting

Auto-forecasting workflow support for production and pressure datasets.

## Included Assets

- MCP server: `mcp-servers/forecasting-mcp`
- Skill: `skills/auto-forecasting`

## Scope

Use this area to profile multi-well production datasets, evaluate available pressure signals, choose eligible forecast method families, identify candidate forecast origins, and produce forecast QC guidance before running deeper Arps or hybrid model fitting.

The current workflow is method-selection and QC oriented. It assumes many real datasets will not contain enough reservoir, PVT, completion, pressure-transient, or operating-detail inputs for full reservoir-engineering calculations. Detailed Arps fitting implementations remain in `OilGas/ArpsForecasting` until they are refactored behind a stable engine contract.
