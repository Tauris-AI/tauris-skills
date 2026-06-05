# Forecasting Claude Cowork Plugin

Installs the forecasting skill and MCP server from the `tauris-skills` Cowork marketplace.

## Install

Add the marketplace from GitHub:

```text
/plugin marketplace add Tauris-AI/tauris-skills
```

Or add it from a local checkout:

```text
/plugin marketplace add "<local repo path>"
```

Install the plugin:

```text
/plugin install forecasting@tauris-skills
```

Fully restart Cowork after installing.

## Marketplace Cache

Important: Cowork caches the marketplace catalog when you add it. After editing `.claude-plugin/marketplace.json` or adding a new plugin, restarting the app is not enough. Force Cowork to re-read the catalog:

```text
/plugin marketplace remove tauris-skills
/plugin marketplace add <github-or-local>
```

Then reinstall the affected plugins.

## Python

`forecasting` uses Python 3.12:

```cmd
py --list
py -3.12 -m pip install fastmcp
```

Cowork launches the server with `py -3.12` from `areas/forecasting/.mcp.json`.

## First Prompt

```text
Use the forecasting-mcp server. Profile this production CSV, identify available oil/gas/water and pressure signals, recommend eligible forecast method families per well, identify candidate forecast origins, and flag wells that need human review before automated fitting.
```
