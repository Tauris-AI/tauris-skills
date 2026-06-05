# PHDWin v2

Read-only PHDWin v2 inspection, extraction, and PHDWin-to-Aries workflow support.

## Included Assets

- Skill: `skills/phdwin-v2-querying`
- MCP server: `mcp-servers/PHDWinv2_MCP`
- PHDWin-to-Aries playbook: `mcp-servers/PHDWinv2_MCP/PHDWIN_TO_ARIES_PLAYBOOK.md`
- PHDWin-to-Aries table map: `mcp-servers/PHDWinv2_MCP/PHDWIN_TO_ARIES_TABLE_MAP.md`
- Aries Access template: external local file, supplied with `ARIES_TEMPLATE_ACCDB_PATH` or `template_accdb_path`
- PHDWin output definitions: `mcp-servers/PHDWinv2_MCP/reference/phdwin-v2/Phdwinout definitions_complete.xls`
- Setup guide: `SME_SETUP_GUIDE.md`
- Copilot prompt: `../../.github/prompts/phdwin-query.prompt.md`

## Scope

Use this area when the task is to inspect a PHDWin `.phz`, `.phd`, `.mod`, or PHDWin report-generated Access database source, list tables, sample rows, run read-only queries, export review data to SQLite or named CSV files, or review PHDWin-to-Aries conversion readiness.

Native PHDWin extraction requires the 32-bit SoftVelocity Clarion / TopSpeed ODBC driver. SQLite review databases do not require that driver.

The public workflow is SQLite-first: use the Clarion driver only long enough to create a local SQLite review database, then perform agent review and CSV/Access staging from SQLite.

The Cowork plugin does not bundle raw `.sqlite`, `.db`, `.mdb`, or `.accdb` template databases under `areas/phdwin-v2` because highly-compressible database blobs can trip Cowork's plugin compression-ratio guard. Generate local SQLite fixtures after install, or point Access export tools at an external cleared Aries `.accdb` template.

PHDWin v2 can also produce Access databases as part of its reports. Treat those `.mdb` or `.accdb` report outputs as inspectable source artifacts when supplied by a user, but inventory their tables and columns before assuming they match native PHDWin extraction tables. Tracking note: `663545`.
