# Forecasting Local E2E Workspace

Use this folder for local end-to-end forecasting skill and MCP tests.

Everything in this folder is git-ignored except this README and the committed
fixtures listed below. Good local-only candidates:

- production and pressure CSV files
- generated profile JSON
- generated chart SVGs
- forecast recommendation outputs
- Cowork transcripts, logs, and screenshots

## Committed fixtures

Anonymized Enverus datasets committed for offline/CI testing. All real
operator, well, location, and regulator identifiers were removed:

- `WellHeaderData.csv` — 90 wells, one row per well. Color+chess `WELL_NAME`
  and `OPERATOR`, 14-digit synthetic `WELL_ID` join key. Surface/bottom-hole
  coordinates and regulator/permit columns (district, survey, abstract,
  section/township, permit dates, lease/unit names) stripped; `STATE` and
  `COUNTY` retained for coarse context.
- `MonthlyProduction.csv` — 3,756 monthly `OIL`/`GAS`/`WATER` rows for the same
  90 wells, joined to the header 1:1 on `WELL_ID`. `OPERATOR` is matched to the
  header (header authoritative).

Generated artifacts (`output/`, `__pycache__/`) remain git-ignored.

Suggested smoke flow:

1. Configure the forecasting MCP server from `areas/forecasting/mcp-servers/forecasting-mcp/cowork_config.example.json`.
2. Place a cleared production/pressure CSV in this folder.
3. Run the profiling/recommendation workflow.
4. Confirm method eligibility, QC flags, and chart output are generated.
5. Compare the result against the committed `scripts/test_forecasting_mcp.py` expectations where practical.
