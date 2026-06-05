# ARIES Claude Cowork Plugin

Installs the ARIES documentation-first skills from the `tauris-skills` Cowork marketplace. The optional MCP server is only for inspecting local ARIES `.accdb` / `.mdb` files when the user supplies one.

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

Python is only needed when using the optional `aries-mcp` Access database inspection server. AC_ECONOMIC documentation review and drafting new lines do not require a database or Python.

`aries-mcp` uses Python 3.12:

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
Use the ARIES area in this repo. Load areas/aries/skills/aries-core/SKILL.md and areas/aries/skills/aries-ac-economic/SKILL.md. For AC_ECONOMIC work, read references/aries-ac-economic-best-practices.md, references/ac-economic-line-grammar.md, references/ac-economic-calculations.md, references/ac-economic-keyword-catalog.md, references/line-format.md, and references/validation-rules.md first. For PHDWin-to-ARIES Python exporter behavior, also read references/phdwin-ac-economic-resolver.md. Draft or review proposed new lines as a dry-run artifact. Do not ask for an ARIES database unless I specifically request database inspection or validation against supplied rows.
```
