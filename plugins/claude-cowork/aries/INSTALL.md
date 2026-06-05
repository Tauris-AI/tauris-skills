# ARIES Claude Cowork Plugin

Installs the ARIES skills and MCP server from the `tauris-skills` Cowork marketplace.

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
/plugin install aries@tauris-skills
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

`aries` uses Python 3.12:

```cmd
py --list
py -3.12 -m pip install fastmcp pyodbc
```

Confirm the Microsoft Access ODBC driver is visible to the same Python:

```cmd
py -3.12 -c "import pyodbc; [print(d) for d in pyodbc.drivers()]"
```

Cowork launches the server with `py -3.12` from `areas/aries/.mcp.json`.

## First Prompt

```text
Use the ARIES area in this repo. Load the ARIES skills, then inspect the supplied ARIES Access database through aries-mcp without writing changes.
```
