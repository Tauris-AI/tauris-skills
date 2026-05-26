---
name: phdwin-v2-querying
description: Use for PhdWIN v2 extraction prerequisites, Clarion driver guidance, extracted table mapping, key/join explanation, safe querying of extracted PhdWIN inputs, and preparing data for Tauris conversion workflows into ARIES.
---

# PhdWIN V2 Querying

Use this skill when a task involves `Tauris.PhdWin`, PhdWIN v2 Clarion/Topspeed datasets, extraction prerequisites, extracted-table interpretation, schema discovery, query drafting, or mapping petroleum-engineering questions onto the PhdWIN data model.

The current verified implementation source is the local repo at `/mnt/c/Dev/Tauris.PhdWin`.
The user-provided document set under `/mnt/c/Dev/Tauris.PhdWin/docs/reference-inputs` must be treated as a primary reference library for PhdWIN v2 behavior, table meaning, conversion context, and business interpretation.

## Adapters

Use agent-specific wrappers from `adapters/` when packaging this skill for other AI systems:

- `adapters/claude.md`
- `adapters/codex.md`
- `adapters/copilot.md`

These files should remain thin. The core domain logic belongs in this `SKILL.md`, `references/`, and `scripts/`.

## Workflow

1. Determine the user's stage:
   - extraction setup
   - extracted-table inspection
   - querying and data lookup
   - ARIES conversion preparation
2. If the user has not extracted data yet, start with extraction prerequisites:
   - explain that PhdWIN v2 uses Clarion TopSpeed (`.tps`) storage
   - explain that a Clarion/TopSpeed ODBC driver is required for direct extraction through the Tauris tooling
   - if the driver is missing, instruct the user to contact Tauris AI or SoftVelocity
   - explain that the target outcome is a set of extracted tables named the way `Tauris.PhdWin` stages them
3. Restate the business question in PhdWIN terms: project, case/well, forecast, owner, group, filter, sort, history, investment, or model variable.
4. Decide the access path:
   - use existing REST endpoints first when the repo already exposes the needed data
   - use `/api/schema` and `/api/schematable` to discover tables and columns
   - use `/api/query` only for read-only SQL that is not already covered by a typed endpoint
5. Identify the minimum required tables and anchor keys before drafting SQL.
6. Explain the extracted table layout in business terms:
   - what table contains the requested inputs
   - which keys join it to surrounding tables
   - whether it is a `PHD_*` or `MOD_*` source
7. Default to read-only work. For exploratory SQL, prefer narrow projections, explicit filters, and small row counts.
8. Resolve table names using the same placeholder rules as `Tauris.PhdWin`:
   - `{{phd}}` resolves to the `.phd` file name.
   - `{{mod}}` resolves to the `.mod` file name.
   - Generated entity annotations such as `{{phd}}\&MAINLSE` are the canonical source of truth.
9. Document dataset assumptions clearly:
   - datasource path or import workspace
   - whether the source is unzipped `.phz`, Access, Excel, or CSV
   - any assumed joins or code mappings
   - any uncertainty around customer-specific customizations
10. When the request is conversion-oriented, connect the PhdWIN tables back to Tauris conversion logic:
   - identify which extracted tables are inputs to the conversion
   - explain the keys and fields required from those tables
   - call out any gaps or assumptions that would block a reliable ARIES export
11. For mutation requests, do not draft direct writes until you have:
   - a dry-run plan
   - exact target rows/tables
   - rollback or restore path
   - explicit approval

## Extraction Guidance

- PhdWIN v2 datasets are Clarion TopSpeed based and require the Clarion/TopSpeed ODBC driver for the direct extraction path used by `Tauris.PhdWin`.
- If the user does not have the driver, tell them they need to obtain it from Tauris AI or SoftVelocity.
- The extraction goal is not just to open the `.phz`; it is to produce extracted tables with stable naming that the Tauris query and conversion workflows understand.
- Keep extraction guidance practical:
  - verify the driver is installed
  - identify the uncompressed dataset folder containing `.phd` and `.mod`
  - confirm the server can enumerate tables
  - confirm the expected `PHD_*` and `MOD_*` surfaces are readable
- Do not imply the driver is optional when the user is trying to extract directly from Clarion sources.

## Query Strategy

- Prefer typed controllers generated from entity annotations for simple table reads such as `/api/mainlse`, `/api/groups`, `/api/filter`, `/api/filterline`, `/api/sort`, `/api/owner`, `/api/monhist`, and `/api/forcast`.
- Prefer higher-level endpoints when the question is about business objects rather than raw tables:
  - project tree
  - project entity
  - project variables
  - forecast formulas and segments
  - ownership summaries
- Use schema inspection endpoints before guessing column names.
- When using raw SQL, mirror the repo's own naming conventions and keep the query portable across sample datasets.

## PhdWIN-Specific Rules

- The `datasource` request header is required by the server. It points at the uncompressed dataset folder or other supported source.
- A directory datasource is treated as PhdWIN/Topspeed by default. The server looks for one `.phd` file and optionally one `.mod` file.
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
- a conversion-readiness checklist for PhdWIN-to-ARIES inputs

## Read These References As Needed

Use the references directory by subfolder:

- `references/workflow/`
  - `extraction-guide.md`: driver requirement, extraction prerequisites, and expected extracted table shape
  - `api-endpoints.md`: verified REST endpoints and request shapes from `Tauris.PhdWin`
  - `query-patterns.md`: safe SQL and endpoint usage patterns
- `references/schema/`
  - `schema-notes.md`: verified schema landmarks, key tables, identifiers, and quirks
  - `generated-entity-map.md`: generated route-to-entity-to-table map built from the current repo
- `references/conversion/`
  - `conversion-input-map.md`: PhdWIN tables that matter for Tauris conversion and ARIES preparation
- `references/source-library/`
  - `reference-inputs-index.md`: guide to the user-provided documents in `Tauris.PhdWin/docs/reference-inputs`

## External Reference Library

When the task needs domain interpretation beyond what is already encoded in the repo, consult the user-provided source library at:

- `/mnt/c/Dev/Tauris.PhdWin/docs/reference-inputs`

Use it selectively:

- extraction and table inventory questions: start with the table/datamodel docs
- forecasting and decline questions: use the ARPS and decline documents
- PhdWIN-to-ARIES mapping questions: use the Tauris notes and revision docs
- output/export questions: use the PHDWin output definitions and sample output files

Do not restate undocumented behavior as fact unless it is supported by either:

- generated entities or checked-in code
- `docs/PHDWIN_DATA_MAP.md`
- the curated reference library above

## Maintenance

- When `Tauris.PhdWin` changes, rebuild the entity map with:

```bash
python3 scripts/build_entity_map.py /mnt/c/Dev/Tauris.PhdWin > references/generated-entity-map.md
```

- Keep this skill grounded in generated entity annotations, controller routes, and checked-in docs, not memory.
