# Forecasting Local E2E Workspace

Use this folder for local end-to-end forecasting skill and MCP tests.

Everything in this folder is ignored except this README. Good candidates:

- production and pressure CSV files
- generated profile JSON
- generated chart SVGs
- forecast recommendation outputs
- Cowork transcripts, logs, and screenshots

Suggested smoke flow:

1. Configure the forecasting MCP server from `areas/forecasting/mcp-servers/forecasting-mcp/cowork_config.example.json`.
2. Place a cleared production/pressure CSV in this folder.
3. Run the profiling/recommendation workflow.
4. Confirm method eligibility, QC flags, and chart output are generated.
5. Compare the result against the committed `scripts/test_forecasting_mcp.py` expectations where practical.
