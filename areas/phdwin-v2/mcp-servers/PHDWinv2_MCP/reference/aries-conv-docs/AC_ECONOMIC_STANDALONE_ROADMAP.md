# AC_ECONOMIC Standalone Roadmap

## Boundary

This repo must remain standalone and externally shareable.

Use `Tauris.PhdWin` as the second-best behavioral roadmap only:

- inspect cleared markdown documents
- inspect generated outputs and table-level behavior when available
- summarize behavior in this repo's own words
- do not copy `.cs` source files
- do not create runtime dependencies on `Tauris.PhdWin`
- do not commit implementation snapshots from another repo

The Python exporter in this repo owns its implementation.

## Current Confirmed State

The PHDWin v2 extraction to SQLite is working for the local Puckett sample. The
current unresolved issue is the SQLite-to-ARIES economic conversion, not the
native PHDWin extraction step.

The exporter currently creates deterministic `AC_ECONOMIC` review rows with
`QUALIFIER = PY_REVIEW` and `KEYWORD` values such as:

- `PY_REVIEW_FORECAST`
- `PY_REVIEW_ECON`
- `PY_REVIEW_SEGMENT`
- `PY_REVIEW_PRODVAL`
- `PY_REVIEW_CUMVOL`

These rows are diagnostic coverage artifacts. They prove which PHDWin source
rows are being seen, but they are not final Aries economic syntax and should not
be presented as completed `AC_ECONOMIC` conversion output.

## Reference Documents

Use these documents as the roadmap inputs:

- `ARIES_CONVERSION_NEXT_STEPS.md`
- `ARIES_ACCESS_EXPORT_PLAN.md`
- `ARIES_MIGRATION_ROADMAP.md`
- `ARIES_ACCESS_TABLE_CONTRACTS.md`
- `AC_ECONOMIC_DEEP_FIDELITY_PLAN.md`
- `PHDWIN_DATA_MAP.md`
- `PHDWIN_TO_ARIES_TABLE_MAP.md`

The practical read from those references is:

- first stabilize the staged table contract
- confirm lease/project selection
- keep source inventory visible table by table
- generate production, test, ownership, project, and scenario tables first
- then implement economic line generation in deliberate phases
- compare selected economic lines against approved expected output

## Working Rule For AC_ECONOMIC

Until final economic generation exists, review rows must stay clearly labeled as
review rows.

Do not silently write `PY_REVIEW` rows as if they are final Aries economics in a
customer-facing export mode. A local review export can include them when the
summary reports that `AC_ECONOMIC` is incomplete.

## Implementation Phases

### Phase 1: Source Inventory Gate

For each project/lease selection, report counts and sample rows from:

- `PHD_FORCAST`
- `PHD_LSESEGMENT`
- `PHD_LSEPRODVAL`
- `PHD_ECON`
- `PHD_INVEST`
- `PHD_INVESTDESCR`
- `PHD_CUMVOL`
- `PHD_OWNER`
- `PHD_GROUPS`
- `MOD_SCEN`
- `MOD_TEMPLATE`

Acceptance gate:

- every source table used by economics is counted
- missing source tables are warnings, not silent empty output
- review rows reconcile to source counts before final line generation begins

### Phase 2: Forecast Line Generator

Build final Aries economic forecast rows from `PHD_FORCAST`, supported by
`PHD_PRODUCTNAMES` and `PHD_CUMVOL` where needed.

Acceptance gate:

- rows are keyed by `PROPNUM`, `SECTION`, and `SEQUENCE`
- section and sequence ordering are deterministic
- product mapping is explicit
- unsupported forecast rows are counted in diagnostics

### Phase 3: Segment And Product Value Generator

Use `PHD_LSESEGMENT` and `PHD_LSEPRODVAL` to generate segment-specific and
product-specific economic assumptions.

Acceptance gate:

- segment joins are lease-scoped
- product value joins are product-scoped
- unmatched product codes are counted
- generated rows are testable without Access ODBC

### Phase 4: Cost, Capital, And Economic Inputs

Map `PHD_ECON`, `PHD_INVEST`, and `PHD_INVESTDESCR`.

Acceptance gate:

- operating cost, taxes, pricing, and capital timing have explicit mappings
- signs and timing conventions are tested
- unmatched investment descriptions are counted

### Phase 5: Scenario, Setup, Lookup, And Sidefile Fidelity

Resolve `MOD_SCEN`, `MOD_TEMPLATE`, setup defaults, lookup values, sidefile
references, and macro behavior as needed.

Acceptance gate:

- every generated `AC_ECONOMIC` qualifier is selectable by `AC_SCENARIO`
- required setup rows are present
- unsupported macros or sidefile references fail loudly or produce explicit
  diagnostics

### Phase 6: Reconciliation

Compare the Python output against a reviewed known-good Aries export for the same
source.

Acceptance gate:

- documented row-count comparison by table
- documented sample line comparison by lease/project
- accepted tolerances are written down
- remaining deltas are explicit

## Harness Expectations

The local E2E harness should classify `AC_ECONOMIC` in one of these states:

- `review_rows_only`: source coverage exists, final Aries economics are not done
- `empty`: no economic output was generated
- `final_rows_present`: final Aries economic rows exist
- `mixed_review_and_final`: fail until intentionally supported

For the current Puckett sample, the expected state is `review_rows_only`.

Final conversion is not complete until the harness can assert:

- no `PY_REVIEW` rows in final export mode
- final `AC_ECONOMIC` row count is greater than zero
- `AC_ECONOMIC.PROPNUM` has no orphans versus `AC_PROPERTY.PROPNUM`
- `AC_ECONOMIC` qualifiers are selectable by `AC_SCENARIO`
- selected rows reconcile to approved expected output
