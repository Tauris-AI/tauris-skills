# PHDWin v2 Local E2E Workspace

Use this folder for local end-to-end PHDWin v2 inspection and PHDWin-to-Aries review tests.

Everything in this folder is ignored except this README. Good candidates:

- local `.phz`, `.phd`, `.mod`, `.mdb`, or `.accdb` source files
- extracted PHDWin folders
- generated SQLite review databases
- Aries-named CSV review exports
- optional Aries Access review exports
- Cowork transcripts, logs, screenshots, and readiness memos

Recommended local layout:

```text
e2e-local/
|-- Phdwinv2-db/        Native PHDWin samples, extracted files, SQLite review DBs, Aries CSV outputs
|-- aries-db/           Cleared Aries `.accdb` / `.mdb` samples for table inventory and Access checks
`-- auto-forecasting/   Monthly production + well metadata ZIPs and generated DCA outputs
```

Suggested smoke flow:

1. Configure the PHDWin v2 MCP server from `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.example.json`.
2. Run `env_check`.
3. Inspect a cleared `.phz` or existing SQLite review database.
4. Export or reuse a SQLite review database.
5. Run `conversion_readiness` and `conversion_profile`.
6. Export Aries-named CSV review tables.
7. Confirm native PHDWin files were not modified.

Useful local E2E checks:

- `.phz -> extracted .PHD/.mod`
- extracted native PHDWin files -> SQLite review database
- SQLite review database -> conversion readiness/profile
- SQLite review database -> Aries SQLite review database
- Aries SQLite review database -> Aries-named CSV folder
- cleared Aries Access database -> table inventory through Access ODBC
- monthly production/well metadata ZIPs -> forecasting batch output
