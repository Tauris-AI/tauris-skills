# PHDWin v2 Local E2E Workspace

Use this folder for local end-to-end PHDWin v2 inspection and PHDWin-to-Aries review tests.

Everything in this folder is git-ignored except this README and the committed
fixtures listed below. Good local-only candidates:

- local `.phz`, `.phd`, `.mod`, `.mdb`, or `.accdb` source files
- extracted PHDWin folders
- generated SQLite review databases
- Aries-named CSV review exports
- optional Aries Access review exports
- Cowork transcripts, logs, screenshots, and readiness memos

## Committed fixtures

- `Phdwinv2-db/Demo.phz` — demo PHDWin v2 archive (renamed to an agnostic
  source name; contains `Demo.PHD` + `Demo.mod`). It is the `.phz` source for
  the `.phz -> extract -> review SQLite -> ARIES` pipeline in
  `run_phdwin_e2e.py`, which extracts it to `output/Demo/`.

Generated artifacts (`output/`, `__pycache__/`) remain git-ignored.

Recommended local layout:

```text
e2e-local/phdwin-v2/
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
7. Export an optional Aries `.accdb` from a cleared Aries Access template.
8. Validate the generated `.accdb` through the Aries MCP module:

```powershell
py -3.12-32 scripts\validate_aries_accdb.py e2e-local\phdwin-v2\Phdwinv2-db\aries-accdb\demo_aries_export.accdb
```

9. Confirm native PHDWin files were not modified.

Useful local E2E checks:

- `.phz -> extracted .PHD/.mod`
- extracted native PHDWin files -> SQLite review database
- SQLite review database -> conversion readiness/profile
- SQLite review database -> Aries SQLite review database
- Aries SQLite review database -> Aries-named CSV folder
- generated Aries `.accdb` -> Aries MCP table inventory, counts, and ownership sample
- cleared Aries Access database -> table inventory through Access ODBC
- monthly production/well metadata ZIPs -> forecasting batch output
