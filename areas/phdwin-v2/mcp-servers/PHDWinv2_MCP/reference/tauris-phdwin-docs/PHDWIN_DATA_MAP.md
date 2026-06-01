# PHDWin Data Map

## Purpose

This document defines the first reusable data map for `PHDWin` imports.

The goal is to use one shared interpretation of the PHDWin database for:

- validating each loaded `.phz` dataset
- confirming the dataset can be read through the Clarion driver
- building diagnostics
- building curated navigation
- supporting scoped exports
- supporting future `PHDWin -> Aries` conversion

The working assumption is that the PHDWin database structure is stable across client datasets, even though row counts and business content vary by import.

## Source References

This public copy is grounded in checked-in Tauris-authored notes and source-code-derived table behavior. Proprietary vendor manuals, help files, private spreadsheets, and internal reference-input documents are intentionally excluded.

Implementation references already in code:

- ImportExposureService.cs
- PostgresImportStagingService.cs
- ARIES_MIGRATION_ROADMAP.md

## Import Validation Goal

Each `.phz` load should eventually be validated in three layers:

1. File/package validity
   - archive opens
   - exactly one usable `.phd` file is present
   - exactly one usable `.mod` file is present when required
   - normalized workspace is created successfully

2. Driver/readability validity
   - Clarion ODBC driver is present
   - `.phd` and `.mod` can both be opened
   - expected core tables can be read
   - extraction produces a non-empty manifest

3. Business/readiness validity
   - core entities exist and have plausible counts
   - critical lookup/grouping data is present
   - production/test date ranges are readable
   - export/navigation surfaces can be built

This data map is mainly for layers `2` and `3`.

## Current Table Groups

The current import harness already classifies extracted tables into:

- `PHD_*`
- `MOD_*`

That split should be preserved as the canonical source grouping.

## Name Crosswalk

PHDWin discussions currently use at least three naming styles:

1. short TPS-style mnemonic
   - example: `ACT`
2. logical harness/export name
   - example: `PHD_MAINLSE`
3. raw extracted source table name
   - example: `New.Phd\&MAINLSE`

The data map should preserve all three so we can move cleanly between:

- PHDWin UI conversations
- reference docs and legacy exports
- current harness diagnostics and exports

| Mnemonic | Logical Name | Typical Raw Source | Current Understanding |
| --- | --- | --- | --- |
| `ACT` | `PHD_MAINLSE` | `*.PHD\&MAINLSE` | Core case/well table |
| `TIT` | `PHD_TITLES` | `*.PHD\&TITLES` | Project header / project description |
| `OWN` | `PHD_OWNER` | `*.PHD\&OWNER` | Ownership rows by case |
| `GRP` | `PHD_GROUPS` | `*.PHD\&GROUPS` | Group / partner definitions |
| `ADJ` | `PHD_ADJOWNER` | `*.PHD\&ADJOWNER` | Adjusted ownership-related rows |
| `FLT` | `PHD_FILTER` | `*.PHD\&FILTER` | Filter headers |
| `FLL` | `PHD_FILTERLINE` | `*.PHD\&FILTERLINE` | Filter rule lines |
| `SRT` | `PHD_SORT` | `*.PHD\&SORT` | Sort/subtotal definitions |
| `DAT` | `PHD_MONHIST` | `*.PHD\&MONHIST` | Monthly historical production |
| `TST` | `PHD_TEST` or other extracted test-history source | to be confirmed from dataset/UI | Test history table name still needs confirmation |
| `CLA` | `PHD_CLASS` | `*.PHD\&CLASS` | Reserve class lookup |
| `CAT` | `PHD_CATEGORY` | `*.PHD\&CATEGORY` | Reserve category lookup |
| `IDC` | `PHD_IDCODES` | `*.PHD\&IDCODES` | Code lookup rows |
| `ILF` | `PHD_IDLABELS` | `*.PHD\&IDLABELS` | Label/lookup definitions |
| `DAT` | `PHD_MONHIST` | `*.PHD\&MONHIST` | Monthly production history |
| `FOR` | `PHD_FORCAST` | `*.PHD\&FORCAST` | Forecast parameters / forecast rows |
| `INV` | `PHD_INVEST` | `*.PHD\&INVEST` | Investment rows |
| `SCE` | `MOD_SCEN` | `*.MOD\&SCEN` | Scenario definitions |
| `MSG` | `MOD_MODSEGMENT` or related `MOD_*` set | to be confirmed | Model opex / price-diff related area |
| `MPV` | `MOD_MODPRODVAL` or related `MOD_*` set | to be confirmed | Model-variable dictionary area |
| `LPV` | `PHD_LSEPRODVAL` | `*.PHD\&LSEPRODVAL` | Case-specific vs model value differences |
| `LSG` | `PHD_LSESEGMENT` | `*.PHD\&LSESEGMENT` | Case-specific segment/opex details |
| `PNF` | `PHD_PRODUCTNAMES` | `*.PHD\&PRODUCTNAMES` | Product code dictionary |
| `CUM` | `PHD_CUMVOL` | `*.PHD\&CUMVOL` | Cumulative forecast/history-related volume table |

Notes:

- some mnemonic mappings are confirmed from generated entity names and current extracted tables
- some `MOD_*` and test-history mappings are still provisional and should be confirmed against the UI and larger sample datasets

### PHD Domain

Represents project, case, ownership, filters, sorts, reporting, and historical production/test style data.

Examples already observed:

- `PHD_TITLES`
- `PHD_MAINLSE`
- `PHD_OWNER`
- `PHD_GROUPS`
- `PHD_FILTER`
- `PHD_FILTERLINE`
- `PHD_SORT`
- `PHD_MONHIST`
- `PHD_RPTSCRPT`
- `PHD_RPTSCRLN`
- `PHD_RPTGRP`
- `PHD_RPTLSE`
- `PHD_CLASS`
- `PHD_CATEGORY`
- `PHD_IDCODES`
- `PHD_IDLABELS`

### MOD Domain

Represents model variables, scenarios, templates, and linked model/value definitions.

Examples already observed:

- `MOD_SCEN`
- `MOD_TEMPLATE`
- `MOD_MODPRODVAL`
- `MOD_MODSEGMENT`
- `MOD_CANPRICE`
- `MOD_CURRENCY`
- `MOD_DEPRECIATION`
- `MOD_TIMESTAMP`

## Domain Map

The business-facing system should be organized around domains, not raw tables.

### Projects

Purpose:

- top-level project identity
- import-level project counts
- default project metadata

Current primary source:

- `PHD_TITLES`

Fields already used or likely important:

- `PROJ_DESCR`
- `MODELSUBDIR`
- `MODELID`
- `GROUPID`
- `ASOF_DATE`
- `DISC_DATE`
- `LASTLSEID`

Current diagnostics:

- `entity:project_count`
- `entity:project_name_count`

Planned navigation:

- project dropdown
- project-level case/well counts
- project-level linked model summary

Validation expectations:

- at least one project row
- non-empty project name
- readable as-of date

### Cases / Wells

Purpose:

- core case/well inventory
- case typing
- lease-level navigation
- most downstream export scoping

Current primary source:

- `PHD_MAINLSE`

Likely important fields:

- `LSE_ID`
- `LSE_NAME`
- `CASETYPE`
- `FLD`
- `RESERVOIR`
- `STATE`
- `OPER`
- class/category references

Current diagnostics:

- `entity:lease_count`
- `entity:field_count`
- `entity:reservoir_count`
- `entity:state_count`
- `entity:operator_count`
- `entity:case_type_count`

Planned navigation:

- cases/wells by project
- cases/wells by partner
- cases/wells by filter
- cases/wells by sort
- case counts by case type

Validation expectations:

- non-empty `LSE_ID` population
- non-empty case/well count
- readable case type values

### Partners

Purpose:

- partner/group navigation
- ownership summaries
- partner-based subset export

Current primary sources:

- `PHD_OWNER`
- `PHD_GROUPS`
- `PHD_ADJOWNER`

Likely important fields:

- `GRP_ID`
- `GRP_DESC`
- `LSE_ID`
- `LSENRI`
- `WRKINT`
- `REVINT`

Current diagnostics:

- `entity:owner_group_count`
- `entity:owner_row_count`

Current curated view:

- `vw_partners`

Planned navigation:

- partner dropdown
- partner -> cases/wells
- partner -> ownership stats

Validation expectations:

- ownership rows load
- group ids are readable
- partner/group descriptions can be resolved where available

### Filters

Purpose:

- show saved PHDWin filter definitions
- eventually resolve which cases/wells fall into each filter

Current primary sources:

- `PHD_FILTER`
- `PHD_FILTERLINE`

Likely important fields:

- `FLT_ID`
- `NAME`
- `SEQNO`
- `FLTFIELD`
- `CONDITION`
- `VALUE`
- `OPERATOR`
- `PRIORITY`

Current curated views:

- `vw_filters`
- `vw_filter_lines`

Planned diagnostics:

- filter count
- filter rule count
- cases/wells per filter

Planned navigation:

- filter dropdown
- selected filter -> resolved case/well list
- selected filter -> resolved counts

Validation expectations:

- filter ids are readable
- filter names are readable
- line items can be associated back to a parent filter

### Sorts

Purpose:

- show saved sort/subtotal definitions
- eventually resolve which cases/wells fall into each sort grouping

Current primary source:

- `PHD_SORT`

Likely important fields:

- `SRT_ID`
- `NAME`
- `SORTFIELD$1..$4`
- `SORTDIR$1..$4`
- `LEVEL$1..$4`
- `TOTALS$1..$4`
- subtotal group fields
- total field definitions

Current curated views:

- `vw_sorts`
- `vw_sort_levels`

Planned diagnostics:

- sort count
- sort level count
- cases/wells per sort

Planned navigation:

- sort dropdown
- selected sort -> resolved case/well list
- selected sort -> grouping preview

Validation expectations:

- sort ids and names are readable
- level fields can be flattened consistently

### Production History

Purpose:

- determine production coverage
- provide min/max production dates
- support subset export and future analytics

Current primary source:

- `PHD_MONHIST`

Current diagnostics:

- `date_range:production:min_month`
- `date_range:production:max_month`

Current curated view:

- `vw_production_date_ranges`

Planned diagnostics:

- monthly production row count
- cases with production
- min/max production month by project or subset

Validation expectations:

- monthly history table exists when expected
- date fields can be interpreted consistently

### Test / Daily Data

Purpose:

- validate operational/test history coverage
- support min/max test dates
- support future well review and export

Reference notes indicate:

- `AC_DAILY / AC_TEST` are important in the Aries mapping notes
- test-related data may require special handling

Current confirmed export detail:

- the Aries template contains both `Daily` and `Test` objects
- the current repo now writes both `AC_TEST` and `AC_DAILY`
- that `AC_TEST` dataset is currently derived from `PHD_DAILY`
- `AC_DAILY` is now exported as a separate table, but its final semantic split from `AC_TEST` still needs confirmation

Current status:

- not yet promoted into diagnostics or curated navigation

Planned diagnostics:

- test data availability
- min/max test date
- cases with test history

Validation expectations:

- identify actual extracted source table(s)
- confirm date field semantics

### Linked Models

Purpose:

- link cases/wells to model scenarios, templates, prices, costs, and variable definitions
- support future “linked price and cost model” review

Current primary sources:

- `MOD_SCEN`
- `MOD_TEMPLATE`
- `MOD_MODPRODVAL`
- `MOD_MODSEGMENT`
- `MOD_CANPRICE`
- additional `MOD_*` support tables

Current diagnostics:

- `entity:scenario_title_count`
- `entity:scenario_row_count`
- `entity:template_row_count`

Reference notes indicate:

- `AC_SETUP` / `AC_SETUPDATA` mapping matters downstream
- partner picklist and daily/test output fields also matter for Aries exports

Planned navigation:

- linked scenarios by project/case
- linked template count by project/case
- linked price/cost model summaries

Validation expectations:

- scenario rows present where expected
- template rows readable
- model linkages resolvable from case/project context

## Current Curated Navigation Goal

The curated layer should become a high-level navigation surface, not just a preview table dump.

Initial navigation targets:

- by Project
- by Partner
- by Filter
- by Sort

For each selected item, the UI should eventually show:

- matching cases/wells
- count of matching cases/wells
- basic case type breakdown
- relevant date range context
- later: linked price/cost/scenario/template summaries

## Current Export Goal

Exports should resolve to one of two modes:

1. `All data`
   - all staged tables for the import job

2. `Resolved subset`
   - all data needed for a selected Project, Partner, Filter, Sort, or future curated entity

This means the data map must support both:

- top-level business entity navigation
- traceability back to raw staged tables

## First Canonical Validation Contract

For a `PHDWin` import to be considered readable and minimally valid, the following should be confirmed:

- `PHD_TITLES` exists and has at least one readable row
- `PHD_MAINLSE` exists and has at least one readable row
- `PHD_OWNER` or `PHD_GROUPS` exists for partner/ownership review
- `PHD_FILTER` and `PHD_SORT` are readable when present
- `PHD_MONHIST` is readable when present
- `MOD_SCEN` and `MOD_TEMPLATE` are readable when present
- source table manifest is non-empty
- logical names resolve cleanly to `PHD_*` / `MOD_*`

These checks are the first candidate startup/import validation rules for each loaded `.phz`.

## Immediate Next Mapping Work

The next pass on this document should tighten table/field detail for:

1. `PHD_TITLES`
2. `PHD_MAINLSE`
3. `PHD_OWNER`
4. `PHD_GROUPS`
5. `PHD_FILTER`
6. `PHD_FILTERLINE`
7. `PHD_SORT`
8. `PHD_MONHIST`
9. test/daily history table identification
10. `MOD_SCEN`
11. `MOD_TEMPLATE`
12. linked price/cost model tables

## Notes

- This document is intentionally business-oriented, not just schema-oriented.
- The database map should be stable across client imports.
- The diagnostics and curated navigation layers should both be driven from this map.
- Aries conversion mapping should eventually reference this same document rather than re-infer business meaning ad hoc.

## Core Table Specs

This section is the first working table-by-table spec for the current diagnostics, curated navigation, and future scoped export work.

### `PHD_TITLES`

Business role:

- project header
- import-level project identity
- global/default metadata for the dataset

Observed cardinality:

- expected to be very small
- often effectively one project header row per imported dataset

Key fields:

- `PROJ_DESCR`
  - project name
  - current project count/name diagnostics already depend on this
- `MODELSUBDIR`
  - likely model grouping or model storage linkage
- `MODELID`
  - likely project/model identifier
- `GROUPID`
  - likely default partner/group linkage
- `ASOF_DATE`
  - as-of/effective date for the dataset
- `DISC_DATE`
  - discount/reference date
- `LASTLSEID`
  - likely latest assigned case/lease id
- `MAXECOYEARS`
  - already used in setup-data generation
- `DEFCURRENCY`
  - default currency
- `DEFCONVENTION`
  - default convention

Likely joins / relationships:

- `GROUPID` -> `PHD_GROUPS.GRP_ID`
- project context fans out to `PHD_MAINLSE`

Current usage in code:

- project diagnostics
- first project exposure view
- setup-data generation uses date/max-econ metadata

Validation checks to add:

- row exists
- `PROJ_DESCR` not blank
- `ASOF_DATE` can be interpreted
- `MAXECOYEARS` is within expected bounds

Navigation/export impact:

- drives project dropdown
- anchors project-scoped export subset logic

### `PHD_MAINLSE`

Business role:

- canonical case/well inventory
- core operational entity table

Observed cardinality:

- many rows per dataset
- likely the primary row set for case/well counts

Key fields:

- `LSE_ID`
  - primary case/well identifier
- `LSE_NAME`
  - case name
- `CASETYPE`
  - case type code
- `PDP_CATEGORY`
  - reserve category
- `RSV_CLASS`
  - reserve class
- `CURARCSEQ`
  - current archive/report linkage
- `FLD`
  - field
- `RESERVOIR`
  - reservoir
- `COUNTY`
  - county
- `STATE`
  - state
- `COUNTRY`
  - country
- `OPER`
  - operator
- `WELL`
  - well name
- `LOCATION`
  - location text
- `GASGATH`
  - gas gatherer
- `OILGATH`
  - oil gatherer
- `SOP`
  - start date
- `EOP`
  - end date
- `TD`
  - total depth
- `WELLTYPE`
  - well type

Likely joins / relationships:

- `LSE_ID` -> `PHD_OWNER.LSE_ID`
- `LSE_ID` -> `PHD_MONHIST.LSE_ID`
- `LSE_ID` -> test/daily history tables once confirmed
- `CURARCSEQ` -> archive/report-related tables
- `RSV_CLASS` / `PDP_CATEGORY` -> `PHD_CLASS` / `PHD_CATEGORY`

Current usage in code:

- lease count and case-type diagnostics
- state/operator/field/reservoir diagnostics
- future staged Aries conversion contract

Validation checks to add:

- non-zero row count
- distinct `LSE_ID` count > 0
- `CASETYPE` values readable
- `LSE_NAME` coverage reasonable

Navigation/export impact:

- all Project / Partner / Filter / Sort navigation should eventually resolve to sets of `LSE_ID`
- most subset exports should be case/well scoped through this table

### `PHD_OWNER`

Business role:

- case-to-partner ownership mapping
- interest and revenue participation data

Key fields:

- `LSE_ID`
  - case/well reference
- `GRP_ID`
  - partner/group reference
- `SEQ`
  - row sequence
- `REVTYPE`
  - revenue type
- `REVVALUE`
  - revenue value
- `RESOLVEDDATE`
  - resolved ownership date
- `LSENRI`
  - net revenue interest at case level
- `WRKINT`
  - working interest
- `REVINT`
  - revenue interest
- `NPINT`
  - net profits interest or similar
- `RPG_ID`
  - likely secondary group/relationship id

Likely joins / relationships:

- `GRP_ID` -> `PHD_GROUPS.GRP_ID`
- `LSE_ID` -> `PHD_MAINLSE.LSE_ID`

Current usage in code:

- partner exposure view
- ownership count diagnostics

Validation checks to add:

- ownership rows exist when partner review is expected
- `GRP_ID` coverage is non-empty
- `LSE_ID` references line up with `PHD_MAINLSE`

Navigation/export impact:

- partner dropdown
- partner -> case list resolution

### `PHD_GROUPS`

Business role:

- group/partner definitions
- group-level defaults

Key fields:

- `GRP_ID`
  - primary group identifier
- `GRP_DESC`
  - group/partner name
- `NUMLEASES`
  - stored lease count
- `OWNER_DEFAULT`
  - default ownership-related value
- `ROY_DEFAULT`
  - default royalty-related value
- `INV_DEFAULT`
  - default investment flag/value
- `ACQ_COST`
  - acquisition cost
- `LOCKINV2MAIN`
  - investment lock behavior

Likely joins / relationships:

- `GRP_ID` <- `PHD_OWNER.GRP_ID`
- `GRP_ID` <- `PHD_TITLES.GROUPID` as default group

Current usage in code:

- partner exposure view

Validation checks to add:

- if ownership rows exist, confirm matching group descriptions can be resolved for most `GRP_ID` values

Navigation/export impact:

- partner naming
- partner picklists

### `PHD_FILTER`

Business role:

- saved filter header definitions

Key fields:

- `FLT_ID`
  - filter id
- `NAME`
  - filter name

Likely joins / relationships:

- `FLT_ID` -> `PHD_FILTERLINE.FLT_ID`

Current usage in code:

- filter exposure view

Validation checks to add:

- filter ids unique
- filter names readable

Navigation/export impact:

- filter dropdown
- filter header list for subset resolution

### `PHD_FILTERLINE`

Business role:

- row-level logic behind each saved filter

Key fields:

- `FLT_ID`
  - parent filter id
- `SEQNO`
  - line sequence
- `OPERATOR`
  - operator code joining logic conditions
- `PRIORITY`
  - evaluation/order priority
- `FLTFIELD`
  - field name being filtered
- `CONDITION`
  - condition operator
- `VALUE`
  - comparison value

Likely joins / relationships:

- `FLT_ID` -> `PHD_FILTER.FLT_ID`

Current usage in code:

- filter-rule exposure view

Validation checks to add:

- filter lines resolve back to known filter ids
- sequence ordering is consistent
- fields/conditions are populated often enough to resolve real filters

Navigation/export impact:

- eventually required to turn a saved filter into an actual set of cases/wells

### `PHD_SORT`

Business role:

- saved sort and subtotal definitions

Key fields:

- `SRT_ID`
  - sort id
- `NAME`
  - sort name
- `MANUALORDER`
  - sort ordering mode
- `TOTALTHRESHOLD`
  - total threshold
- `SUBTOTALTHRESHOLD`
  - subtotal threshold
- `SORTFIELD$1..$11`
  - sort fields
- `SORTDIR$1..$11`
  - direction per sort level
- `LEVEL$1..$11`
  - level metadata
- `SUBTOTALGROUP$...`
  - subtotal grouping fields
- `TOTALFIELD$...`
  - total field definitions

Likely joins / relationships:

- currently appears self-contained
- may later need linkage to report screen or case-level output logic

Current usage in code:

- sort exposure view
- sort-level flattening view

Validation checks to add:

- sort ids unique
- sort names readable
- at least one sort field exists on defined sorts

Navigation/export impact:

- sort dropdown
- sort -> resolved case grouping preview

### `PHD_MONHIST`

Business role:

- monthly production history

Key fields:

- `LSE_ID`
  - case/well reference
- `TYPE`
  - record/product type
- `YEAR`
  - production year
- `PROD1TD..PROD5TD`
  - total-to-date style values
- `PROD1$1..$12`
  - monthly series 1
- `PROD2$1..$12`
  - monthly series 2
- `PROD3$1..$12`
  - monthly series 3
- `PROD4$1..$12`
  - monthly series 4
- `PROD5$1..$12`
  - monthly series 5

Open question:

- exact semantic mapping of `PROD1..PROD5` still needs confirmation from docs or sample outputs

Likely joins / relationships:

- `LSE_ID` -> `PHD_MAINLSE.LSE_ID`

Current usage in code:

- min/max production month diagnostics
- production date range curated view

Validation checks to add:

- rows exist when production is expected
- year values are in plausible bounds
- monthly arrays contain some non-zero data

Navigation/export impact:

- project/partner/filter/sort subset date range summaries
- production coverage review

### `MOD_SCEN`

Business role:

- scenario definitions in the model layer

Key fields:

- `SEQ`
  - scenario sequence/id
- `PRIEXP`
  - pricing/expense mode indicator
- `PRODUCTNAME`
  - product linkage
- `TITLE`
  - scenario title
- `MODPOINTER`
  - pointer to model/variable definition
- `MODPICK`
  - selection flag
- `TIMESTAMP`
  - version/time marker

Likely joins / relationships:

- `MODPOINTER` likely links into model-variable definitions such as `MOD_MODPRODVAL`

Current usage in code:

- scenario title and row-count diagnostics

Validation checks to add:

- titles readable
- enough scenario rows exist when model review is expected

Navigation/export impact:

- linked scenario summaries
- future scenario-based subset views

### `MOD_TEMPLATE`

Business role:

- template/regime definitions in the model layer

Key fields:

- `TPL_ID`
  - template id
- `REGIMEFOLDER`
  - regime grouping folder
- `REGIME`
  - regime name
- `CURRENCY`
  - template currency
- `TIMESTAMP`
  - version/time marker
- `MEMO`
  - freeform notes

Likely joins / relationships:

- likely linked downstream to scenario/model configuration and export setup

Current usage in code:

- template row-count diagnostics

Validation checks to add:

- template rows readable
- regime names and currency values present where expected

Navigation/export impact:

- linked template summaries by project/case

## Join Backbone

The current likely join backbone for diagnostics and navigation is:

- `PHD_TITLES`
  - project header / defaults
- `PHD_MAINLSE`
  - core case/well inventory
- `PHD_OWNER`
  - ownership rows by case
- `PHD_GROUPS`
  - partner/group names
- `PHD_FILTER` + `PHD_FILTERLINE`
  - saved filter definitions
- `PHD_SORT`
  - saved sort definitions
- `PHD_MONHIST`
  - monthly production
- `MOD_SCEN` + `MOD_TEMPLATE`
  - first model-layer linkage metadata

The most important technical principle is:

- resolved navigation should ultimately produce sets of `LSE_ID`
- export subsets should then be derived from those resolved `LSE_ID` sets plus linked supporting rows

## Next Field-Level Questions

The next pass should answer:

1. What is the exact business meaning of each `CASETYPE` value?
2. Which table actually carries test-history rows for diagnostics and navigation?
3. How should saved filters be resolved into `LSE_ID` sets?
4. How should saved sorts be resolved into `LSE_ID` groupings?
5. Which `MOD_*` tables link price and cost models back to cases or projects?
6. Which tables define report-screen and output navigation relevance?
