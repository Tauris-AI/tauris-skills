# Reference Templates

This folder documents local reference templates that agents can use for review workflows.

The Cowork plugin intentionally does not ship raw `.sqlite`, `.db`, `.mdb`, or `.accdb` database templates under `areas/phdwin-v2`. These files can compress far past Cowork's plugin compression-ratio guard and cause plugin install failure.

## Files

- `Aries_Template.accdb` - external local Access template used when Access ODBC is available; set `ARIES_TEMPLATE_ACCDB_PATH` or pass `template_accdb_path`.
- `aries_access_template.sqlite` - optional local SQLite copy generated from an external `Aries_Template.accdb`; useful when an agent needs the Access-template table/view inventory without using Access ODBC.
- `aries_review_template.sqlite` - optional local SQLite review template for agents that can query SQLite more easily than Access.
- `phdwin_review_template.sqlite` - generated local synthetic one-lease PHDWin review template with 76 `PHD_`/`MOD_` source tables for source-side PHDWin-to-Aries workflow testing.

## SQLite Template Scope

`aries_access_template.sqlite` is generated directly from an external cleared Access template. Use it for local SQLite inspection of the Access-template table structure, Access query/view objects, and seed/reference rows. Access views are represented as SQLite views backed by materialized `__access_view_*` tables. It is still a template copy, not a client database.

`aries_review_template.sqlite` is not a full ARIES vendor database clone. It is a neutral review fixture with ARIES-style table names and representative columns for agent testing, mapping review, and prompt development.

`phdwin_review_template.sqlite` is not converted from client PHDWin data. It is a synthetic one-lease fixture based on the documented PHDWin review table map plus the MCP server's 76-table default `PHD_`/`MOD_` source surface. The core conversion tables contain fabricated one-lease rows; less-certain tables contain placeholder rows so agents can test table discovery, joins, and missing-column behavior without client files. All identifiers, names, locations, dates, volumes, and economics are fabricated.

Use it to:

- test that an agent can open and query a SQLite economics/review database
- prototype PHDWin-to-Aries review prompts without client data
- inspect common concepts such as property identity, ownership, forecasts, production history, economics, prices, costs, capital, taxes, and group membership
- test source-side PHDWin review prompts without a Clarion/TopSpeed driver or client files

Do not use it as:

- a production ARIES schema contract
- a replacement for the Access template
- evidence of vendor-specific behavior beyond the documented review concepts
- evidence of actual PHDWin client data or vendor-specific values
- a substitute for a real native PHDWin export when column-level fidelity matters

## Claude Code Prompt

```text
Use the `create_phdwin_review_template` MCP tool to create a local synthetic SQLite fixture, then inspect that generated file.

Inspect the tables and summarize what economic concepts are represented. Treat this as a scrubbed review fixture, not a production ARIES database.
```

## Template Build

Generate the PHDWin SQLite fixture through Cowork:

```text
Use the phdwin-v2 MCP server. Create a PHDWin review template at C:\Path\To\phdwin_review_template.sqlite.
```

Or regenerate SQLite templates from the repository root on a Windows machine with 32-bit Python, `pyodbc`, an external cleared Access template, and the Access ODBC driver:

```cmd
py -3.12-32 scripts\build_reference_sqlite_templates.py ^
  --access-template C:\Path\To\Aries_Template.accdb ^
  --aries-sqlite C:\Path\To\aries_access_template.sqlite ^
  --phdwin-sqlite C:\Path\To\phdwin_review_template.sqlite
```
