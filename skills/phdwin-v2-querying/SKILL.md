---
name: phdwin-v2-querying
description: Use for PhdWIN v2 extraction prerequisites, Clarion driver guidance, SQLite extracted table mapping, key/join explanation, and safe read-only querying of extracted PhdWIN inputs using reusable lookup logic.
---

# PhdWIN V2 Querying

Use this skill when a task involves a local PhdWIN v2 implementation, PhdWIN v2 Clarion/Topspeed datasets, extraction prerequisites, SQLite extracted-table interpretation, schema discovery, read-only query drafting, or mapping petroleum-engineering questions onto the PhdWIN data model.

The current verified implementation source is the local PhdWIN implementation repo.
The user-provided document set under the local `docs/reference-inputs` folder must be treated as a primary reference library for PhdWIN v2 behavior, table meaning, query context, and business interpretation.

## Adapters

Use agent-specific wrappers from `adapters/` when packaging this skill for other AI systems:

- `adapters/claude.md`
- `adapters/codex.md`
- `adapters/copilot.md`

These files should remain thin. The core domain logic belongs in this `SKILL.md`, `references/`, and `scripts/`.

## Execution Boundary

This skill provides PhdWIN v2 domain knowledge, schema references, query patterns, and extraction guidance.

PhdWIN is a Windows desktop application. In normal use, `.phz`, `.phd`, `.mod`, and related dataset artifacts live on the user's local machine or another local Windows-accessible environment.

It does **not** directly query `.phd`, `.mod`, `.tps`, or `.phz` files unless the runtime environment has access to:

- Windows
- Clarion / TopSpeed ODBC driver
- `pyodbc` or another ODBC client
- the extracted PhdWIN dataset folder
- permission to execute local scripts

Cloud-hosted AI environments usually cannot access the user's local ODBC driver. In those environments, the skill should generate scripts, SQL, API wrappers, or troubleshooting steps rather than claiming it can query the dataset directly.

## Workflow

1. Determine the user's stage:
   - extraction setup
   - extracted-table inspection
   - querying and data lookup
   - reusable select-query design
2. Determine the source type first:
   - native PhdWIN input: `.phz`, `.phd`, `.mod`
   - extracted SQLite database: `.sqlite`, `.db`
3. If the source type is native PhdWIN, start with extraction prerequisites:
   - explain that PhdWIN v2 uses Clarion TopSpeed (`.tps`) storage
   - explain that a Clarion/TopSpeed ODBC driver is required for the supported direct extraction workflow
   - if the driver is missing, instruct the user to obtain and install it before attempting native extraction
   - explain that the target outcome is a set of extracted SQLite tables named consistently with the local implementation
4. If the source type is extracted SQLite:
   - skip the Clarion driver prerequisite
   - confirm that the SQLite file exists and opens
   - confirm that the expected extracted tables are present
   - keep the guidance SQLite-oriented
5. Restate the business question in PhdWIN terms: project, case/well, forecast, owner, group, filter, sort, history, investment, or model variable.
6. Decide the access path:
   - use existing REST endpoints first when the repo already exposes the needed data
   - use `/api/schema` and `/api/schematable` to discover tables and columns
   - use `/api/query` only for read-only SQL that is not already covered by a typed endpoint
7. Identify the minimum required tables and anchor keys before drafting SQL.
8. Explain the extracted table layout in business terms:
   - what table contains the requested inputs
   - which keys join it to surrounding tables
   - whether it is a `PHD_*` or `MOD_*` source
9. Default to read-only work. For exploratory SQL, prefer narrow projections, explicit filters, and small row counts.
10. Resolve table names using the same placeholder rules as the local implementation:
   - `{{phd}}` resolves to the `.phd` file name.
   - `{{mod}}` resolves to the `.mod` file name.
   - Generated entity annotations such as `{{phd}}\&MAINLSE` are the canonical source of truth.
11. Document dataset assumptions clearly:
   - datasource path or import workspace
   - whether the source is unzipped `.phz`, Access, Excel, CSV, or extracted SQLite
   - any assumed joins or code mappings
   - any uncertainty around customer-specific customizations
12. When the request comes from prior ARIES-conversion work, reuse that logic as read-only lookup logic:
   - identify which extracted PhdWIN or SQLite tables answer the question
   - explain the keys and fields required from those tables
   - keep the result as `SELECT`-style guidance or endpoint calls only
   - do not drift into export or mutation logic unless explicitly requested
13. For mutation requests, do not draft direct writes until you have:
   - a dry-run plan
   - exact target rows/tables
   - rollback or restore path
   - explicit approval

## Expected Workflow

When a user wants to work with a local `.phz` file from the PhdWIN desktop application:

1. Treat `.phz` as a ZIP-style package when possible.
2. Extract or inspect it.
3. Locate the `.Phd` and optional `.MOD` files.
4. Tell the user the dataset folder, not the file, is the ODBC target.
5. Use the Clarion / TopSpeed ODBC driver locally.
6. Run read-only schema discovery first.
7. Generate safe SQL against known PhdWIN tables.
8. Export results to CSV, SQLite, or JSON for downstream analysis.

Preferred pipeline:

```text
.phz
  -> extract .Phd / .MOD
  -> Clarion TopSpeed ODBC
  -> Python pyodbc runner
  -> CSV / SQLite / API
  -> AI analysis
```

Treat `.phz`, `.phd`, and `.mod` as local desktop-side artifacts. Do not imply that a cloud agent can directly open them unless the execution environment is actually local and Windows-capable.

## Codex Behavior

When running inside Codex CLI or a local IDE agent, first determine whether the environment can actually execute the workflow.

Check for:

- Operating system
- Python version
- `pyodbc`
- available ODBC drivers
- dataset folder path
- presence of `.Phd` / `.MOD`
- whether the user is running in Windows or WSL

If the user is in WSL but the ODBC driver is installed on Windows, do not assume Linux Python can use it. Prefer Windows Python, PowerShell, or a local Windows API bridge.

Codex should not fabricate query results. If the driver or dataset is unavailable, produce a runnable script and explain what the user must run locally.

## Recommended Local Runner

The skill should help generate a local runner in this order:

- `list_odbc_drivers.py` - prints installed ODBC drivers
- `extract_phz.py` - extracts `.phz` into a dataset folder
- `smoke_test.py` - attempts read-only queries against core tables
- `export_sqlite.py` - exports selected PhdWIN tables to SQLite
- `api_server.py` - optional FastAPI wrapper exposing schema/query endpoints
- `phdwin_wizard.py` - optional interactive wrapper around the core steps
- `run_phdwin_wizard.sh` - optional shell launcher for the wizard

All generated code must default to read-only access.

Preferred implementation order:

1. `list_odbc_drivers.py`
2. `extract_phz.py`
3. `smoke_test.py`
4. `export_sqlite.py`
5. optional `api_server.py`
6. optional `phdwin_wizard.py`

Preferred command-line workflow:

```text
python list_odbc_drivers.py
python extract_phz.py <file.phz>
python smoke_test.py <dataset-folder>
python export_sqlite.py <dataset-folder> <output.sqlite>
```

Treat the wizard as convenience only. Do not make it the primary execution path until the lower-level scripts are proven on real client machines.

## Extraction Guidance

- PhdWIN v2 datasets are Clarion TopSpeed based and require the Clarion/TopSpeed ODBC driver for the supported direct extraction path.
- If the user does not have the driver, tell them they need to obtain and install it before attempting native extraction.
- The extraction goal is not just to open the `.phz`; it is to produce extracted SQLite tables with stable naming that downstream query workflows understand.
- Keep extraction guidance practical:
  - verify the driver is installed
  - identify the uncompressed dataset folder containing `.phd` and `.mod`
  - confirm the server can enumerate tables
  - confirm the expected `PHD_*` and `MOD_*` surfaces are readable
- Do not imply the driver is optional when the user is trying to extract directly from Clarion sources.

## SQLite Guidance

- If the user already has an extracted SQLite database, the Clarion driver is not needed for query work.
- For SQLite-first work, validate:
  - the SQLite file exists
  - the database opens successfully
  - the expected extracted tables are present
  - the expected key columns are present
- Keep SQLite guidance read-only unless the user explicitly asks for mutation.
- Reuse the same table meaning and key logic as the native PhdWIN extraction path.

## Safety and Data Handling

PhdWIN files may contain confidential reserves, production, ownership, and economic data.

Default behavior:

- read-only queries only
- no destructive SQL
- no writes back to `.Phd`, `.MOD`, or `.tps`
- avoid uploading customer datasets unless explicitly approved
- prefer local extraction to CSV/SQLite for sharing
- redact sensitive owner/entity names when creating examples

## Query Strategy

- Prefer typed controllers generated from entity annotations for simple table reads such as `/api/mainlse`, `/api/groups`, `/api/filter`, `/api/filterline`, `/api/sort`, `/api/owner`, `/api/monhist`, and `/api/forcast`.
- Prefer higher-level endpoints when the question is about business objects rather than raw tables:
  - project tree
  - project entity
  - project variables
  - forecast formulas and segments
  - ownership summaries
- Use schema inspection endpoints before guessing column names.
- When using raw SQL, mirror the repo's own naming conventions and keep the query portable across sample datasets and extracted SQLite tables.
- Prefer answering with read-only `SELECT` logic or equivalent endpoint calls.

## Primary Use Cases

- list projects or cases
- identify where ownership data lives
- find forecast inputs for a given well
- find initial oil decline rate for a given well and stream
- inspect saved filters and sorts
- explain which key fields join the relevant tables
- translate prior ARIES-conversion extraction logic into standalone read-only lookups

## PhdWIN-Specific Rules

- The `datasource` request header is required by the server. It points at the uncompressed dataset folder or other supported source.
- A directory datasource is treated as PhdWIN/Topspeed by default. The server looks for one `.phd` file and optionally one `.mod` file.
- If the data has already been extracted into SQLite, use the same table names and key logic but keep guidance SQLite-oriented rather than ODBC-oriented.
- Clarion date values are stored as integers and often exposed in the entities with companion `*_dttm` not-mapped properties. In raw SQL, treat the base integer column as the source of truth unless the API already materializes the converted date.
- Many PhdWIN tables use one-based array columns such as `segmentdate$1` or `prod1$12`. The generated entities flatten these into .NET arrays for API use, but raw SQL must use the literal column names with `$n`.
- `FORCAST` is intentionally misspelled in the source data and in the generated entity/table annotation. Do not "correct" it to `FORECAST`.
- The ODBC driver is fragile. Avoid aggregate-heavy or unnecessarily complex exploratory SQL when a typed endpoint or staged export can answer the question more safely.
- Do not rely on the SQL Server stub in `OdbcConnectionFactory`; it contains hardcoded connection details and is not the PhdWIN query path this skill is for.

## Expected Outputs

Depending on the request, produce one of these:

- extraction prerequisites and next steps
- a table map showing where the requested data lives
- a key/join explanation for the relevant tables
- a safe query or endpoint call
- a read-only lookup plan expressed as `SELECT` logic

## Read These References As Needed

Use the references directory by subfolder:

- `references/workflow/`
  - `extraction-guide.md`: driver requirement, extraction prerequisites, and expected extracted table shape
  - `api-endpoints.md`: verified REST endpoints and request shapes from the local PhdWIN implementation
  - `query-patterns.md`: safe SQL and endpoint usage patterns
- `references/schema/`
  - `schema-notes.md`: verified schema landmarks, key tables, identifiers, and quirks
  - `generated-entity-map.md`: generated route-to-entity-to-table map built from the current repo
- `references/lookups/`
  - `select-query-map.md`: PhdWIN tables and fields for common read-only lookup questions
- `references/source-library/`
  - `reference-inputs-index.md`: guide to the user-provided documents in the local `docs/reference-inputs` folder

## External Reference Library

When the task needs domain interpretation beyond what is already encoded in the repo, consult the user-provided source library in the local `docs/reference-inputs` folder.

Use it selectively:

- extraction and table inventory questions: start with the table/datamodel docs
- forecasting and decline questions: use the ARPS and decline documents
- lookup questions derived from prior ARIES-conversion work: use the local notes and revision docs only as mapping aids, then keep the final answer read-only
- output/export questions: use the PHDWin output definitions and sample output files

Do not restate undocumented behavior as fact unless it is supported by either:

- generated entities or checked-in code
- `docs/PHDWIN_DATA_MAP.md`
- the curated reference library above

## Maintenance

- When the local PhdWIN implementation changes, rebuild the entity map with:

```bash
python3 scripts/build_entity_map.py /path/to/phdwin-implementation > references/generated-entity-map.md
```

- Keep this skill grounded in generated entity annotations, controller routes, and checked-in docs, not memory.
