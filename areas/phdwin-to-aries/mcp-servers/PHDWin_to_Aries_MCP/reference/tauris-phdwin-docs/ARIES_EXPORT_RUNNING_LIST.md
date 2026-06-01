# Aries Export Running List

Updated: 2026-05-12

This is the current handoff note for the Aries Access export work in the local PHDWin import harness.

## Current State

The Aries Access export is now producing a downloadable `.accdb` that opens in Aries.

Confirmed working:

- Aries export can generate a downloadable database
- `AC_PROPERTY` structure looked good in testing
- lease-scoped export is working for the lease-linked row tables, including `AC_ECONOMIC`
- `AC_SETUP` is now treated as template-owned
- `AC_SETUPDATA` now needs additive behavior, not replace behavior
- the latest change was to append generated Taurus setup rows to `AC_SETUPDATA` instead of deleting existing template rows

Recent implementation notes:

- Aries export currently copies the template database and writes into that copy
- many Aries data tables are written into existing template tables instead of always dropping/recreating
- `AC_SETUPDATA` was changed to append into the existing template table instead of truncating it
- `AC_SETUP` is not currently written by the export and should remain template-driven

## Confirmed Table Behavior

### Lease-scoped data tables

These should reflect the selected Aries export lease scope:

- `AC_PROPERTY`
- `AC_PRODUCT`
- `AC_TEST`
- `AC_DAILY`
- `AC_ECONOMIC`

### Template-owned tables

- `AC_SETUP`
  - should remain template-driven
  - expected to be one row
  - do not rebuild it

### Additive template tables

- `AC_SETUPDATA`
  - preserve template-defined rows
  - append Taurus `TAURIS / FRAME` lines
  - do not replace/truncate the table

## Clarion Date Confirmation

PHDWin `AsOf` values are Clarion dates.

Confirmed conversion:

- raw `82123`
- converted `11/01/2025`

Repo logic:

- `ClarionDateExtensions.GetDateTimeFromClarionDate(int phdDate)`
- base date: `1800-12-28`
- formula: `1800-12-28 + phdDate days`

## Project Membership First

Current priority has changed.

Before further sort/filter implementation work, the next mapping pass should lock down:

- `PROJECT`
- `PROJLIST`
- `AC_PROPERTY`
- `SelFilters`
- `SORTFILTERS`

Current working interpretation:

- `PROJLIST` is the critical bridge between project identity and property membership
- `AC_PROPERTY.PROPNUM` is the key property/case anchor
- `SelFilters` and `SORTFILTERS` are project behavior tables whose meaning depends on project membership
- partner projects should be ownership-driven
- source-side `GROUPS` are being used as incrementals
- source-side `GROUPLIST` is the member list for those economic difference entities

Current source-side project model:

- one default dataset project such as `00_RSV_CAT`
- partner projects derived from qualified ownership
- incremental/group projects derived from `PHD_GROUPS` + `PHD_LIST`

Current implementation direction:

- create `00_RSV_CAT` as a synthetic default Aries project
- present that default project to users as `All Cases`
- exclude source group `All Cases` from explicit Aries project rows
- build non-default project membership from `PHD_LIST` first
- use `PHD_OWNER` `SEQ = 1` only as a fallback membership source when list rows are absent
- generate stable Aries starter `SelFilters` / `SORTFILTERS` rather than depend on any presumed active PHDWin sort/filter state
- when no explicit sort is available, default the sort stack from `RSV_CAT`
- treat resolved Aries PostgreSQL tables as the primary export contract for `.accdb` generation when a resolved schema exists
- treat `AC_PROPERTY` as export-owned: recreate it from the resolved Aries shape instead of preserving the template table schema

For the moment:

- ignore `GROUPTEST`

Reason:

- the primary export risk is project membership and project behavior mapping, not downstream group test output

## Sorts and Filters

These remain major export targets, but they are now second to the project-membership chain above.

### Selection filters table

Target table name:

- `SelFilters`

Observed columns:

- `ProjKey`
- `SeqNum`
- `TableAlias`
- `TableColumn`
- `Operator`
- `OperatorText`
- `AndOr`
- `DataType`

Observed examples:

- `TAI_EXCLUDE is Null`
- `RSV_CAT is one of PDP, PUD, PROB`
- `LSE_ID is one of 2.00`

Notes:

- `DataType = 12` for text-style filters
- `DataType = 8` for numeric-style filters
- the older placeholder logic in `OwnershipRepository.GetSelFiltersTable()` is too simplistic for the current target behavior

### Sort definitions table

Target table name:

- `SORTFILTERS`

Observed columns:

- `ProjKey`
- `SeqNum`
- `TableAlias`
- `TableColumn`
- `SortOrder`
- `SortBreak`

Observed examples:

- `CLASS`
- `RSV_CLASS`
- `RSV_CAT`
- `STATE`
- `FIELD`
- `LEASE`
- `RSC_SORT`
- `LSE_ID`

Notes:

- sort stacks vary by project
- the older placeholder logic in `OwnershipRepository.GetSortFiltersTable()` is also too simplistic for the current target behavior

## Template Metadata Notes

Observed:

- `DBSLIST` is not currently written by export
- if the exported database shows a DB label like `TEST`, that is coming from the template copy

Implication:

- any desired DB label override such as `PHDCONV` must either:
  - be preconfigured in the template
  - or be explicitly written later if we decide to own that behavior in code

## Current Gaps / Next Work

1. `PROJLIST` lease scoping
   Only exported lease IDs should appear in `PROJLIST`.

2. Sort/filter export
   Write `SelFilters` and `SORTFILTERS` into the Aries Access export using the actual template-backed table names and structures above.

3. Project-specific sort/filter generation
   Replace the old placeholder `OwnershipRepository` logic with logic that matches the real project definitions we want in Aries after `PROJECT` / `PROJLIST` / `AC_PROPERTY` mapping is confirmed.
   Current scoped export now uses stable starter rows instead of active saved PHDWin sort/filter inference.

4. Export-path architecture
   Keep fixing semantics in `PHDWin staged Postgres -> Aries resolved Postgres`.
   The Access export should prefer loading from `aries_*` resolved tables rather than rebuilding those rows on the fly from staged source data.

5. Document source-side incremental semantics
   Treat `GROUPS` as incremental economic entities and `GROUPLIST` as the source-side member list for those entities.

6. Diagnostics date formatting
   Show converted Clarion dates like `11/01/2025`, not only raw values like `82123`.

7. Admin purge validation
   Validate the new purge workflow in the UI after rebuild/restart:
   - delete import workspaces on disk
   - drop all `job_*` and `aries_*` schemas
   - clear UI job state cleanly

## Important Testing Notes

- For setup-data testing, reconversion is usually not required if only the `AC_SETUPDATA` export write behavior changed
- restart and rerun the export first
- reconvert only if the underlying resolved Aries job content changed

## Files Most Relevant To Resume

- `src/Tauris.PhdWin.Server/Endpoints/Imports/ImportExportService.cs`
- `src/Tauris.PhdWin.Server/Endpoints/ModelVariable/ModelVariableRepository.cs`
- `src/Tauris.PhdWin.Server/Endpoints/Ownership/OwnershipRepository.cs`
- `src/Tauris.PhdWin.Server/Endpoints/Aries/ImportScopedAriesService.cs`
- `docs/ARIES_ACCESS_TABLE_CONTRACTS.md`
- `docs/ARIES_AC_PROPERTY_RULES.md`
- `docs/ARIES_SCHEMA_MAPPING.md`
- `docs/ARIES_SCHEMA_EVIDENCE.md`
