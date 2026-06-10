# AC_ECONOMIC Deep Fidelity Plan

## Purpose

This plan defines the work required to make the Python Cowork MCP package generate high-fidelity Aries `AC_ECONOMIC` rows from PHDWin v2 SQLite exports.

Current status:

- the Python exporter generates structural Aries review tables
- `AC_ECONOMIC` now emits deterministic Python review rows from `PHD_FORCAST`, `PHD_ECON`, `PHD_INVEST`, `PHD_LSESEGMENT`, `PHD_LSEPRODVAL`, `MOD_SCEN`, `MOD_TEMPLATE`, and `PHD_CUMVOL`
- these rows are coverage artifacts, not verified final Aries economic syntax
- generated CSV/ACCDB outputs are review artifacts, not final economics parity outputs

The goal is to move from a placeholder `AC_ECONOMIC` surface to a deterministic Python resolver that can be tested and reconciled without bundling Tauris C# source code.

For the externally shareable repo boundary and implementation sequence, also see
`AC_ECONOMIC_STANDALONE_ROADMAP.md`.

## Runtime Boundary

The Cowork MCP package is Python-only at runtime.

Do not bundle C# implementation snapshots into this repo. Use cleared markdown
notes, cleared reference artifacts, and known-good input/output examples to
define behavior.

## Source Inputs

The deep resolver must inventory and interpret at least:

- `PHD_FORCAST`
- `PHD_LSESEGMENT`
- `PHD_LSEPRODVAL`
- `PHD_ECON`
- `PHD_INVEST`
- `PHD_INVESTDESCR`
- `PHD_CUMVOL`
- `PHD_OWNER`
- `PHD_GROUPS`
- `PHD_LIST`
- `PHD_PRODUCTNAMES`
- `PHD_IDCODES`
- `PHD_IDLABELS`
- `MOD_SCEN`
- `MOD_TEMPLATE`

Missing optional tables should produce warnings and diagnostics, not silent empty output.

## Target Contract

The resolver must explicitly define:

- `AC_ECONOMIC` columns written by the Python exporter
- effective key: `PROPNUM`, `SECTION`, `SEQUENCE`
- section names and section ordering
- sequence ordering within each section
- scenario handling
- product stream handling
- forecast segment ordering
- price/differential handling
- operating cost handling
- investment/capital handling
- ownership/effective interest handling when it affects economics
- unsupported row preservation strategy

Do not infer final Aries table/column names from DTOs, JSON keys, or source field casing.

## Implementation Shape

Use a dedicated Python module:

- `scripts/aries_economic.py`

The module should expose a narrow interface:

```python
build_ac_economic_rows(source_tables, selected_lease_ids=None) -> result
```

The result should include:

- generated `AC_ECONOMIC` rows
- warnings
- per-table source row counts
- missing table list
- unsupported source row counters
- per-lease generated row counts

`scripts/aries_export.py` should call this module instead of embedding economic logic directly.

## Phased Work

### Phase 1: Inventory And Diagnostics

- centralize `AC_ECONOMIC` generation in `scripts/aries_economic.py`
- report source economic table counts
- report missing required/recommended economic tables
- keep generated rows empty until behavior is specified
- expose warnings in `aries-export-summary.json`

### Phase 2: Forecast Skeleton

- generate deterministic forecast sections from `PHD_FORCAST`
- preserve lease scope
- preserve product code and sequence order
- include diagnostics for ignored forecast rows
- add golden tests for one-lease and multi-lease fixture cases

Initial implementation note:

- rows use `KEYWORD = PY_REVIEW_FORECAST`
- rows use `QUALIFIER = PY_REVIEW`
- rows use `SECTION = 1`
- `EXPRESSION` and `LINE` preserve selected source field/value pairs for review
- this deliberately avoids pretending to generate verified ARIES forecast syntax before the field contract is curated

### Phase 3: Cost, Capital, And Econ Inputs

- map `PHD_ECON`
- map `PHD_INVEST`
- map `PHD_INVESTDESCR`
- map value overrides from `PHD_LSEPRODVAL`
- map segment context from `PHD_LSESEGMENT`
- add sign/timing checks

Initial implementation note:

- `PHD_ECON` rows use `KEYWORD = PY_REVIEW_ECON`
- `PHD_INVEST` rows use `KEYWORD = PY_REVIEW_INVEST`
- `PHD_LSESEGMENT` rows use `KEYWORD = PY_REVIEW_SEGMENT`
- `PHD_LSEPRODVAL` rows use `KEYWORD = PY_REVIEW_PRODVAL`
- `MOD_SCEN` rows use `KEYWORD = PY_REVIEW_SCEN`
- `MOD_TEMPLATE` rows use `KEYWORD = PY_REVIEW_TEMPLATE`
- `PHD_CUMVOL` rows use `KEYWORD = PY_REVIEW_CUMVOL`
- these rows preserve selected source field/value pairs for review
- `PHD_INVESTDESCR` is joined into investment review rows when a common description identifier is present
- unmatched investment description identifiers are counted in diagnostics
- product names from `PHD_PRODUCTNAMES` are appended to review rows when product codes match
- unmatched product codes are counted by source table

### Phase 4: Scenario, Template, Lookup, And Sidefile Fidelity

- interpret `MOD_SCEN`
- interpret `MOD_TEMPLATE`
- add lookup/macro support as required
- preserve unsupported lines or emit explicit review diagnostics
- reconcile generated setup/scenario dependencies

### Phase 5: Reconciliation

- compare Python output against known-good reviewed outputs
- document accepted deltas
- add regression fixtures for fixed defects
- only then remove the "review artifact" warning for supported economics surfaces

## Test Requirements

Add tests that can run without ODBC:

- create small SQLite fixtures in temp directories
- call `build_ac_economic_rows`
- call `export_aries`
- assert `AC_ECONOMIC.csv` content
- assert warning text for missing economic tables
- assert lease-scoped filtering

Avoid tests that require client files, PHDWin native files, Access ODBC, or vendor help/manual content.

## Acceptance Criteria

Deep fidelity is not complete until:

- source table diagnostics explain every missing or unused economic input
- generated `AC_ECONOMIC` rows are deterministic
- section and sequence ordering are tested
- known-good examples reconcile within documented tolerances
- unsupported behavior is explicit in warnings or diagnostics
- no C# source is bundled in this MCP package
