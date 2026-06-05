# Petroleum Economics Claude Cowork Plugin

Installs the petroleum economics review skill from the `tauris-skills` Cowork marketplace. This plugin is skill-only and does not have an MCP server.

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

No Python interpreter or MCP dependencies are required for this skill-only plugin. For the other plugins, verify Python installs with:

```cmd
py --list
```

`phdwin-v2` needs `py -3.12-32`; `aries` and `forecasting` use `py -3.12`.

## First Prompt

```text
Use the petroleum economics review skill. Review the supplied economics assumptions and outputs, separate source evidence from assumptions, and identify missing ownership, price, tax, forecast, cost, capital, and payout details.
```
