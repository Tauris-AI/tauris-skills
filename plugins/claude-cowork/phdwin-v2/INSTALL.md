# PHDWin v2 Claude Cowork Plugin

Installs the PHDWin v2 skills and MCP server from the `tauris-skills` Cowork marketplace.

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
/plugin install phdwin-v2@tauris-skills
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

`phdwin-v2` requires a side-by-side 32-bit Python 3.12 for the Clarion/TopSpeed ODBC driver. Verify it is available:

```cmd
py --list
```

Install dependencies into that interpreter:

```cmd
py -3.12-32 -m pip install -r C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\requirements.txt
```

Confirm the 32-bit SoftVelocity TopSpeed ODBC driver is visible:

```cmd
py -3.12-32 -c "import pyodbc; [print(d) for d in pyodbc.drivers()]"
```

Cowork launches the server with `py -3.12-32` from `areas/phdwin-v2/.mcp.json`.

## First Prompt

```text
Use the phdwin-v2 MCP server. Run env_check and tell me whether this machine is ready to inspect PHDWin v2 sources and create SQLite review artifacts.
```
