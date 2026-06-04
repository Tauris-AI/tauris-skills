# Forecasting Claude Cowork Plugin

Installs the forecasting MCP server for Claude Cowork.

## Canonical Files

- Area: `areas/forecasting`
- Skill: `areas/forecasting/skills/auto-forecasting`
- MCP server: `areas/forecasting/mcp-servers/forecasting-mcp`
- Cowork config: `areas/forecasting/mcp-servers/forecasting-mcp/cowork_config.example.json`

## Install

1. Clone or unpack this repo to:

```text
C:\Dev\tauris-skills
```

2. Install Python packages:

```cmd
py -3.12 -m pip install fastmcp
```

3. Open Claude Cowork -> Settings -> Developer -> Edit Config.

4. Merge the `forecasting-mcp` entry from:

```text
C:\Dev\tauris-skills\areas\forecasting\mcp-servers\forecasting-mcp\cowork_config.example.json
```

5. Fully restart Claude Cowork.

## First Prompt

```text
Use the forecasting-mcp server. Profile this production CSV, identify available oil/gas/water and pressure signals, recommend eligible forecast method families per well, identify candidate forecast origins, and flag wells that need human review before automated fitting.
```

## Notes

This plugin supports limited-data production forecasting. It should use AI to help write and choose forecasting methods, fit-window logic, and QC explanations. It should not pretend to run a full reservoir-engineering calculation when reservoir, PVT, completion, pressure-transient, or operating details are missing.
