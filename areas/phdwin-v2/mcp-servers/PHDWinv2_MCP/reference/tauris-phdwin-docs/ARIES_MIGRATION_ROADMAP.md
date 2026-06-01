# Aries Migration Roadmap

## Goal

Make `Tauris.PhdWin` the canonical repo for:

- `PHDWin -> staged import`
- `Aries -> staged import`
- `PHDWin -> Aries conversion`
- eventual `Aries .accdb/.mdb` export

The near-term goal is narrower:

- upload a `PHDWin` dataset
- stage it locally and/or in Postgres
- generate Aries-ready artifacts from the staged job context
- remove dependence on the live ODBC-backed repository path for conversion

## Current State

Implemented now:

- source-aware imports for `PHDWin` and `Aries`
- staged workspace + Postgres staging
- Postgres-first staged table reads with workspace fallback
- batched `aries_*` resolved writes for import-scoped conversion
- JSON Aries bundle export for the current live datasource path
- import-job-scoped staged table reader
- import-job-scoped lease validation
- import-job-scoped master-table generation

Still not implemented:

- managed typed Postgres conversion tables over `job_*`
- staged `LeaseViewModel` / project context
- staged forecast econ generation
- staged project-variable econ generation
- staged ownership econ generation
- staged Aries reference bundle generation
- dependency-aware `AC_ECON` scheduling for incremental / chained cases
- native Aries Access database writing

Current refactor update:

- POSTGRES_ARIES_REFACTOR_UPDATE.md

## Build Order

### 1. Stabilize the staged table contract

Lock down the first table set we will support for staged conversion:

- `PHD_MAINLSE`
- `PHD_PRODUCTNAMES`
- `PHD_TITLES`
- `PHD_OWNER`
- `PHD_GROUPS`
- `PHD_CLASS`
- `PHD_CATEGORY`
- `PHD_IDCODES`
- `PHD_IDLABELS`
- `PHD_FORCAST`
- `PHD_LSEPRODVAL`
- `PHD_LSESEGMENT`
- `PHD_INVEST`
- `PHD_INVESTDESCR`
- `MOD_*` tables required for sidefiles and model-variable expansion

Deliverable:

- documented required-table contract for staged Aries conversion

### 2. Build staged project context

Create the staged equivalent of the core `IProjectRepository` data we need:

- staged `LeaseViewModel`
- staged `CurrArcSeq`
- staged metadata
- staged master row
- staged master-table definition

Deliverable:

- service that can answer lease/project context questions for an import job without live ODBC

### 3. Build staged lease selection and validation

Expand import-scoped Aries services to support:

- list staged lease ids
- validate staged lease ids
- fetch core staged lease information

Deliverable:

- stable import-job lease selector for downstream conversion and tests

### 4. Port forecast econ generation

Refactor the logic behind `GetForecastEconlines(...)` so it can run on staged input rows instead of live repository queries.

This is the largest single implementation step because it is the core of `PHDWin -> Aries`.

Deliverable:

- staged forecast-to-Aries econ generation for a lease

### 5. Port project-variable econ generation

Refactor the logic behind `ProjectVariableRepository.GetEconlines(...)` so it can run from staged `LSEPRODVAL`, `LSESEGMENT`, `MODPRODVAL`, `MODSEGMENT`, and related model-variable rows.

Deliverable:

- staged project-variable Aries econ lines

### 6. Port ownership and reference export pieces

Move the simpler remaining paths off live repositories:

- ownership econ lines
- project table
- groups table
- group list table
- sort filters
- selection filters
- setup/reference rows

Deliverable:

- staged reference bundle support

### 7. Build a staged Aries export bundle

Create an import-job-based bundle generator that produces:

- staged lease bundle
- staged reference bundle

Deliverable:

- import-job-based Aries JSON bundle output

### 8. Swap import export over to staged execution

Update `aries_bundle` export so imported `PHDWin` jobs use the staged path by default rather than the live datasource path.

Deliverable:

- real `uploaded PHDWin -> Aries bundle` flow

### 9. Add native Aries database writing

Once the staged Aries bundle is stable, add:

- Access database writer
- table creation / append logic
- download packaging

Deliverable:

- `uploaded PHDWin -> Aries .accdb/.mdb`

## Testing Strategy

Yes, building tests and a small test harness with sample databases makes sense. It is the right approach.

This work is too transformation-heavy to rely on manual verification alone.

We should have both:

- unit tests for deterministic mapping/transformation logic
- an integration-style harness for sample `PHDWin` and `Aries` datasets

### Unit Tests

Best targets for unit tests:

- logical table name normalization
- staged row-to-entity mapping
- lease/master row generation
- reserve category mapping
- product/sidefile mapping helpers
- formula/token transformation helpers
- econ line ordering and section sequencing

These should live in:

- test/Tauris.PhdWin.Test

### Integration / Fixture Tests

Best targets for fixture-driven tests:

- import a known `PHDWin` sample
- verify staged tables are present
- verify row counts for key tables
- verify staged master-table row for known lease ids
- verify Aries bundle structure for a known lease
- compare selected econ lines against approved expected output

These can run against:

- workspace-staged JSON files
- and later Postgres-backed staged jobs

### Test Harness

The harness should be intentionally narrow:

- feed a sample import job
- inspect staged outputs
- run staged Aries bundle generation
- dump artifacts for human review

That is more useful right now than trying to build a large generic test app.

Use these existing starting points:

- docs/LOCAL_IMPORT_HARNESS.md
- test/BlazorServerTestHarness
- testdata

## Suggested Test Assets

We should keep at least three representative fixtures:

1. Small `PHDWin` sample

- minimal lease count
- enough forecast/project-variable/ownership data to exercise conversion

2. Medium `PHDWin` sample

- enough variety to expose edge cases
- multiple leases
- multiple products
- sidefile usage

3. Aries reference sample

- known-good Aries output structure for comparison

If possible, also store expected outputs for a few known lease ids:

- expected staged master row
- expected reference bundle fragments
- expected Aries econ snippets

## Rough Effort

These estimates assume one person working directly in this repo with reasonable continuity.

### Fastest useful milestone

`uploaded PHDWin -> staged Aries JSON bundle for a limited lease set`

Estimated time:

- about `2 to 4 weeks`

This assumes:

- staged project context is implemented
- forecast econ logic ports cleanly enough
- we accept JSON bundle output first

### Full staged conversion milestone

`uploaded PHDWin -> staged Aries JSON bundle` with broader reference support and better confidence

Estimated time:

- about `4 to 8 weeks`

This includes:

- forecast econ
- project-variable econ
- ownership/reference tables
- fixture-based validation

### Native Aries database export milestone

`uploaded PHDWin -> working Aries .accdb/.mdb`

Estimated time:

- about `6 to 10+ weeks`

This depends heavily on:

- how strict Aries table compatibility needs to be
- whether the current generated bundle already matches all required Aries semantics
- Access writing and validation effort

## Recommendation

Do not try to jump directly to `.accdb` writing.

Build in this order:

1. staged project context
2. staged forecast econ conversion
3. staged project-variable and ownership conversion
4. staged JSON Aries bundle
5. fixture validation
6. native Aries database writing

That keeps the hardest logic visible and testable before we add Access file-writing complexity.

## Immediate Next Step

Implement staged project context first, then add tests around it before porting forecast econ logic.
