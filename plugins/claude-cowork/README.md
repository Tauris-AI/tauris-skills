# Claude Cowork Plugins

This repo publishes a Claude Cowork marketplace named `tauris-skills`.
Cowork installs four plugins from that marketplace:

- `phdwin-v2`
- `aries`
- `forecasting`
- `petroleum-economics`

## Install

In the Cowork UI, open the plugin **Directory** -> **Plugins** -> **Personal** tab -> **+** (**Add marketplace**) -> **Add from a repository**, then enter the GitHub `owner/repo` or git URL (`https://github.com/Tauris-AI/tauris-skills`) and confirm. Only add marketplace sources you trust. (Screenshots of this flow are embedded in `Tauris_Skills_AI_Platform_Install_Guide.md`.)

Or add the marketplace from GitHub with a slash command:

```text
/plugin marketplace add Tauris-AI/tauris-skills
```

Or add it from a local checkout:

```text
/plugin marketplace add "<local repo path>"
```

Install the plugins:

```text
/plugin install phdwin-v2@tauris-skills
/plugin install aries@tauris-skills
/plugin install forecasting@tauris-skills
/plugin install petroleum-economics@tauris-skills
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

`phdwin-v2` needs a side-by-side 32-bit Python 3.12 because the Clarion/TopSpeed ODBC driver is 32-bit:

```cmd
py --list
py -3.12-32 -m pip install -r C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\requirements.txt
```

`aries` and `forecasting` use 64-bit Python 3.12:

```cmd
py -3.12 -m pip install fastmcp pyodbc
```

## Plugin Sources

Each Cowork plugin source is an `areas/<name>` folder. Cowork discovers skills from the plugin's `skills/` directory and MCP servers from `.mcp.json` at the plugin root. `petroleum-economics` is skill-only and does not have an MCP config.
