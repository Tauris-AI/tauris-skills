# Forecasting Area - SME Setup Guide

Lets Claude Cowork profile production and pressure CSVs, recommend forecast method families per well, and identify wells that need human forecast review.

## Prerequisites

```cmd
py -3.12 -m pip install fastmcp
```

## Register With Claude Cowork

1. Open Cowork.
2. Open Settings.
3. Go to Developer.
4. Click Edit Config.
5. Add the MCP entry from:

```text
areas/forecasting/mcp-servers/forecasting-mcp/cowork_config.example.json
```

6. Fully restart Cowork.

## Recommended Prompt

```text
Use the forecasting-mcp server. Profile this production CSV, summarize which wells have pressure data, recommend eligible forecast method families per well, and flag wells that need human forecast review before automated fitting.
```

## Guardrails

- Treat pressure as context and QC signal before using it as a model feature.
- Detect candidate forecast origins before fitting; do not assume first production is always the right start date.
- Do not force the same model stack onto every well.
- Prefer candidate curves plus diagnostics over a silent one-curve answer.
