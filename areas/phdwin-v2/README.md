# PHDWin v2

Read-only PHDWin v2 inspection, extraction, and PHDWin-to-Aries workflow support.

## Included Assets

- Skill: `skills/phdwin-v2-querying`
- MCP server: `mcp-servers/PHDWinv2_MCP`
- PHDWin-to-Aries playbook: `mcp-servers/PHDWinv2_MCP/PHDWIN_TO_ARIES_PLAYBOOK.md`
- PHDWin-to-Aries table map: `mcp-servers/PHDWinv2_MCP/PHDWIN_TO_ARIES_TABLE_MAP.md`
- Aries Access template: `mcp-servers/PHDWinv2_MCP/reference/templates/Aries_Template.accdb`
- Setup guide: `SME_SETUP_GUIDE.md`
- Copilot prompt: `../../.github/prompts/phdwin-query.prompt.md`

## Scope

Use this area when the task is to inspect a PHDWin `.phz`, `.phd`, or `.mod` source, list tables, sample rows, run read-only queries, export review data to SQLite or named CSV files, or review PHDWin-to-Aries conversion readiness.

Native PHDWin extraction requires the 32-bit SoftVelocity Clarion / TopSpeed ODBC driver. SQLite review databases do not require that driver.

The public workflow is SQLite-first: use the Clarion driver only long enough to create a local SQLite review database, then perform agent review and CSV/Access staging from SQLite.
