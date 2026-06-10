---
name: aries-core
description: Use for ARIES application workflows, ARIES Access export review, PHDWin-to-Aries conversion logic, cross-table ARIES petroleum economics context, project/member/filter/sort mapping, and conversion QA based on Tauris.PhdWin behavior. Use this before narrower ARIES skills when the task spans AC_PROPERTY, AC_ECONOMIC, AC_OWNER, AC_PRODUCT, AC_DAILY, AC_TEST, PROJECT, PROJLIST, SelFilters, SORTFILTERS, setup data, scenarios, lookups, or Access export.
---

# ARIES Core

This is the broad ARIES operating skill for Tauris conversion work. It is system-aware but should stay export-format agnostic where possible: reason about ARIES target tables, semantics, keys, and review behavior first; only then decide whether the output should be Access, SQLite, CSV, JSON, or a dry-run memo.

Use this skill when an agent must understand or review how PHDWin v2 data becomes ARIES-ready data through the Tauris.PhdWin conversion model.

## Operating Rules

1. Treat ARIES output as contract-driven, not a generic table dump.
2. Treat PHDWin source extraction as read-only. Never mutate native PHDWin files.
3. Prefer SQLite review databases for agent analysis. Use Clarion / TopSpeed ODBC only for the one-time native PHDWin extraction step.
4. Keep the Clarion / TopSpeed driver serialized: one native extraction job at a time per machine/process.
5. For mutating ARIES workflows, produce a dry-run artifact and review summary before writing.
6. Do not invent ARIES field meanings. Mark unknown behavior as unverified.
7. Preserve template-owned ARIES data unless a human explicitly approves taking ownership of it.
8. Preserve unsupported or unknown rows. Do not drop data just because the current converter cannot interpret it.
9. Use Tauris.PhdWin reference logic as the primary behavioral guide for PHDWin-to-Aries conversion.
10. Use deterministic scripts or table checks for repeatable validation whenever available.

## When To Load Other Files

Load these only when the task requires the detail:

- `references/module-map.md`: ARIES area/module routing.
- `references/aries-access-payload-contract.md`: shared payload contract for builders that write ARIES Access databases.
- `references/aries-access-write-checklist.md`: shared Access writer safety and integrity rules.
- `../aries-ac-economic/SKILL.md`: detailed `AC_ECONOMIC` parsing, validation, taxonomy, Tauris conversion best practices, and line editing.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/PHDWIN_TO_ARIES_TABLE_MAP.md`: PHDWin source table map.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/PHDWIN_TO_ARIES_PLAYBOOK.md`: Cowork workflow for PHDWin-to-Aries review.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs/ARIES_ACCESS_TABLE_CONTRACTS.md`: fixed ARIES Access table contracts.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs/ARIES_SCHEMA_MAPPING.md`: project/member/filter/sort mapping notes.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs/ARIES_EXPORT_RUNNING_LIST.md`: latest export-state and known gaps.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs/ARIES_AC_PROPERTY_RULES.md`: strict `AC_PROPERTY` rules.
- `../../../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/phdwin-v2/Phdwinout definitions_complete.xls`: cleared PHDWin output table/field definitions for source interpretation.

## Standard Workflow

1. Identify the ARIES target surface:
   `AC_PROPERTY`, `AC_ECONOMIC`, `AC_OWNER`, `AC_PRODUCT`, `AC_DAILY`, `AC_TEST`, `PROJECT`, `PROJLIST`, `SelFilters`, `SORTFILTERS`, `AC_SCENARIO`, `AC_SETUPDATA`, `ARLOOKUP`, sidefiles, groups, or Access export.
2. Identify the source layer:
   native PHDWin `.phz/.phd/.mod`, exported SQLite, staged CSV, resolved ARIES SQLite/Postgres, or existing ARIES Access template/export.
3. Separate extraction from conversion:
   native PHDWin -> SQLite review database -> resolved ARIES tables -> Access/CSV/QA outputs.
4. Determine scope:
   all leases, one `LSE_ID`, a project, a filter, a sort, or an ownership/partner subset.
5. Check key source tables before mapping:
   `PHD_MAINLSE`, `PHD_OWNER`, `PHD_FORCAST`, `PHD_MONHIST`, `PHD_GROUPS`, `PHD_LIST`, `PHD_PRODUCTNAMES`.
6. Build or review the ARIES target rows against fixed target table contracts.
7. Validate keys, row counts, missing memberships, duplicate target keys, and template-owned/additive table behavior.
8. Return a concise memo with source path, scope, tables reviewed, conversion risks, and recommended next action.

## Conversion Architecture

The preferred public workflow is SQLite-first:

```text
PHDWin .phz / .phd + .mod
  -> one serialized Clarion / TopSpeed ODBC extraction
  -> SQLite review database
  -> resolved ARIES table rows
  -> named CSV files and/or Access template copy
  -> human review in ARIES
```

Do not design agent workflows that repeatedly query native PHDWin through the Clarion driver. Once SQLite exists, all deeper review should use SQLite or staged table files.

The resolved ARIES layer should be scoped and replaceable:

- `ConvertAll`
- `ConvertLease(LSE_ID)`
- later `ConvertProject(PROJKEY)`
- later `ConvertFilter(FLT_ID)`
- later `ConvertSort(SRT_ID)`

For `ConvertLease(LSE_ID)`, delete/rebuild only lease-scoped resolved rows for that lease and leave unrelated rows intact.

## PHDWin Source Tables

Use these PHDWin tables as the main conversion inputs:

| PHDWin source | Conversion role |
|---|---|
| `PHD_TITLES` | dataset title/project header/default context |
| `PHD_MAINLSE` | core case/well/property source; primary `LSE_ID` anchor |
| `PHD_PRODUCTNAMES` | product code labels |
| `PHD_OWNER` | ownership and partner context |
| `PHD_GROUPS` | group/project/incremental definitions |
| `PHD_LIST` | explicit project/group membership |
| `PHD_ADJOWNER` | adjusted ownership review |
| `PHD_FORCAST` | forecast rows; preserve source spelling |
| `PHD_LSEPRODVAL` | case/product value overrides |
| `PHD_LSESEGMENT` | lease segment and forecast/economic detail |
| `PHD_MONHIST` | monthly production history |
| `PHD_CUMVOL` | cumulative volume context |
| `PHD_ECON` | economic assumptions |
| `PHD_INVEST` | investment/capital rows |
| `PHD_INVESTDESCR` | investment labels/descriptions |
| `MOD_SCEN` | model/scenario assumptions when present |
| `MOD_TEMPLATE` | model templates and assumptions when present |
| `PHD_FILTER`, `PHD_FILTERLINE` | saved filter definitions |
| `PHD_SORT` | saved sort/subtotal definitions |
| `PHD_CLASS`, `PHD_CATEGORY` | reserve class/category lookup |
| `PHD_IDCODES`, `PHD_IDLABELS` | field/operator/basin/custom code lookup context |

Missing optional tables should be reported as risk or limitation, not fatal by default. Missing core tables such as `PHD_MAINLSE`, `PHD_OWNER`, `PHD_FORCAST`, or `PHD_MONHIST` are conversion risks.

## ARIES Target Areas

| ARIES target | Primary source |
|---|---|
| `AC_PROPERTY` | `PHD_MAINLSE`, title/context, reserve class/category, ID lookup tables |
| `AC_OWNER` | `PHD_OWNER`, `PHD_GROUPS`, `PHD_ADJOWNER` |
| `GROUPTEST` | group/member/test shape only when source rows match template requirements |
| `AC_PRODUCT` | `PHD_MONHIST`, product names, forecast/history context |
| `AC_DAILY` | daily source rows when present; do not duplicate test rows as daily production |
| `AC_TEST` | test/daily test source rows when present |
| `AC_ECONOMIC` | forecast, segment, product value, econ, investment, model scenario/template logic |
| `PROJECT` | default project, partner projects, PHDWin groups/incrementals |
| `PROJLIST` | project membership from `PHD_LIST`, fallback from ownership when necessary |
| `SelFilters` | project-level selection/filter behavior |
| `SORTFILTERS` | project-level sort stack behavior |
| `AC_SCENARIO` | group/model scenario data |
| `AC_SETUPDATA` | generated Tauris setup rows appended to template rows |
| `ARLOOKUP` | code/product/class/category lookup rows |
| sidefiles | resolved sidefile/economic auxiliary data |

## Key Anchors

The source key is usually `LSE_ID`. Preserve it through diagnostics and resolved rows whenever practical.

Important source joins:

- case/well: `PHD_MAINLSE.LSE_ID`
- ownership: `PHD_OWNER.LSE_ID`, `PHD_OWNER.GRP_ID`, `PHD_OWNER.SEQ`
- groups/projects: `PHD_GROUPS.GRP_ID`, `PHD_LIST.GRP_ID`, `PHD_LIST.LSE_ID`
- forecasts: `PHD_FORCAST.LSE_ID`, `ARCSEQ`, `PRODUCTCODE`
- history: `PHD_MONHIST.LSE_ID`, `TYPE`, `YEAR`
- filters: `PHD_FILTER.FLT_ID`, `PHD_FILTERLINE.FLT_ID`
- sorts: `PHD_SORT.SRT_ID`

Important ARIES target keys:

| Table | Effective key |
|---|---|
| `AC_PROPERTY` | `DBSKEY`, `PROPNUM` |
| `AC_PRODUCT` | `PROPNUM`, `P_DATE` |
| `AC_DAILY` | `PROPNUM`, `D_DATE` |
| `AC_TEST` | `PROPNUM`, `T_DATE` |
| `AC_ECONOMIC` | `PROPNUM`, `SECTION`, `SEQUENCE` |
| `AC_OWNER` | `PROPNUM`, `SCENARIO`, `PHASENAME`, `STARTDATE` |
| `PROJECT` | `PROJE`, `PROJKEY` |
| `PROJLIST` | `PROJKEY`, `PROJSEQ` |
| `AC_SCENARIO` | `DBSKEY`, `SCEN_NAME`, `DATA_SECT` |
| `AC_SETUPDATA` | non-keyed/additive |
| `ARLOOKUP` | `NAME`, `LINETYPE`, `SEQUENCE` |

## Project Model

Tauris.PhdWin conversion logic treats ARIES project behavior as first-class. Do not treat groups, filters, and sorts as decorative metadata.

Use three project types:

1. Default dataset project:
   - project key: `00_RSV_CAT`
   - user-facing intent: `All Cases`
   - synthetic default, not a direct copy of source group `All Cases`
2. Partner projects:
   - ownership-driven
   - derive from qualified ownership context
   - not the same thing as PHDWin group/incremental objects
3. Incremental/group projects:
   - source: `PHD_GROUPS` plus `PHD_LIST`
   - represent economic difference entities
   - may include visible incremental member cases

Priority chain:

```text
PHD_GROUPS / PHD_LIST / PHD_OWNER
  -> PROJECT
  -> PROJLIST
  -> AC_PROPERTY.PROPNUM
  -> SelFilters
  -> SORTFILTERS
```

Build project membership from `PHD_LIST` first when it exists. Use `PHD_OWNER SEQ = 1` only as fallback membership source. Keep ownership as qualified-interest logic, not the primary membership list.

## AC_PROPERTY Rules

`AC_PROPERTY` is the highest-priority structural table.

Hard rules:

- table name must be `AC_PROPERTY`
- final Access columns are uppercase
- no spaces or punctuation in final columns
- preserve underscores where needed
- required key pair: `DBSKEY`, `PROPNUM`
- treat `DBSKEY + PROPNUM` as unique
- do not derive final column casing from C# property names or dictionary keys

Core structural fields include:

- `DBSKEY`
- `PROPNUM`
- `SEQ`
- `MAJOR`
- `PRIOR_OIL`
- `PRIOR_GAS`
- `PRIOR_WTR`

Use the template as schema guidance, but Tauris export rules override loose dynamic naming.

## AC_ECONOMIC Rules

Use the narrower `aries-ac-economic` skill for detailed line parsing, validation, taxonomy, and Tauris conversion best practices.

At this level, remember:

- `AC_ECONOMIC` is lease-scoped.
- key shape is `PROPNUM`, `SECTION`, `SEQUENCE`.
- final row shape preserves `PROPNUM`, `SECTION`, `SEQUENCE`, `QUALIFIER`, `KEYWORD`, and `EXPRESSION`.
- Tauris conversion methods are the preferred best-practice source for line generation and resolution until the Python MCP exporter reaches parity.
- forecast rows come primarily from `PHD_FORCAST`.
- production/economic detail may also require `PHD_LSESEGMENT`, `PHD_LSEPRODVAL`, `PHD_ECON`, `PHD_INVEST`, `PHD_INVESTDESCR`, `MOD_SCEN`, and `MOD_TEMPLATE`.
- sidefile expansion, lookup expansion, setup common/default lines, scenario selection, and macro substitution are fidelity risks.
- unsupported economic rows should be preserved unless a human explicitly approves dropping or rewriting them.

If asked to generate or edit actual economic lines, load `aries-ac-economic` plus its best-practices, grammar, calculation, keyword-catalog, line-format, and validation references before drafting output.

## Actuals: AC_PRODUCT, AC_DAILY, AC_TEST

Use production history and actuals tables carefully:

- `AC_PRODUCT` is primarily monthly product/history output.
- `AC_TEST` is test data output.
- `AC_DAILY` is daily production output when a source daily production table exists.
- Do not duplicate test rows into `AC_DAILY` as production.
- If daily source rows are absent, report that `AC_DAILY` cannot be populated from current evidence rather than fabricating rows.

For each lease-scoped output table, row counts should be reconcilable to selected `LSE_ID` scope.

## Ownership And Groups

Ownership is not merely project membership.

Use `PHD_OWNER` for qualified interests, partner context, phases, scenarios, and `AC_OWNER` output. Use `PHD_GROUPS` and `PHD_LIST` for group/incremental project behavior.

Review risks:

- `PHD_MAINLSE` rows with no ownership rows
- owners/groups that do not join cleanly
- duplicate owner rows for the same target key
- adjusted ownership rows in `PHD_ADJOWNER` that change the intended output
- named groups that share visible lease membership but differ by ownership or economic context

`GROUPTEST` is lower priority than project membership and should be skipped unless source rows match the Access table shape.

## Filters And Sorts

`SelFilters` and `SORTFILTERS` describe project behavior in ARIES. Their meaning depends on `PROJECT`, `PROJLIST`, and `AC_PROPERTY`.

`SelFilters` commonly includes:

- `ProjKey`
- `SeqNum`
- `TableAlias`
- `TableColumn`
- `Operator`
- `OperatorText`
- `AndOr`
- `DataType`

Known filter examples:

- `TAI_EXCLUDE is Null`
- `RSV_CAT is one of PDP, PUD, PROB`
- `LSE_ID is one of 2.00`

`SORTFILTERS` commonly includes:

- `ProjKey`
- `SeqNum`
- `TableAlias`
- `TableColumn`
- `SortOrder`
- `SortBreak`

Known sort columns:

- `CLASS`
- `RSV_CLASS`
- `RSV_CAT`
- `STATE`
- `FIELD`
- `LEASE`
- `RSC_SORT`
- `LSE_ID`

When explicit sort/filter logic is incomplete, generate stable starter rows rather than pretending to infer the last active PHDWin UI state. Default sort stack can start from reserve category/class behavior such as `RSV_CAT` when no explicit source is available.

## Scenario And Setup Data

`AC_SETUP` is template-owned and should generally not be rebuilt.

`AC_SETUPDATA` is additive:

- preserve template-defined rows
- append generated Tauris setup rows
- do not truncate the table unless explicitly instructed

`AC_SCENARIO` should be generated from group/model scenario context when present. Validate `DBSKEY`, `SCEN_NAME`, and `DATA_SECT` uniqueness where practical.

## Access Export Behavior

For Aries Access `.accdb` export:

1. Copy the template database first.
2. Prefer writing into existing template tables when their structure is authoritative.
3. Use fixed Aries table names and explicit column mappings.
4. Do not infer table names from DTOs, filenames, JSON keys, or C# property names.
5. Preserve template-owned tables such as `AC_SETUP`.
6. Append to additive tables such as `AC_SETUPDATA`.
7. Recreate or write export-owned lease tables from resolved ARIES rows:
   `AC_PROPERTY`, `AC_PRODUCT`, `AC_TEST`, `AC_DAILY`, `AC_ECONOMIC`.
8. Validate duplicate effective keys before insert where practical.
9. Preserve row order where order is part of the contract, especially `PROJLIST`.
10. Treat Access ODBC and column/type coercion failures as export issues, not source-data truth.

Resolved ARIES tables should be the preferred export contract when available. The Access writer should not rebuild semantic conversion ad hoc if a resolved layer already exists.

## Date Handling

PHDWin dates may be Clarion dates. Use:

```text
date = 1800-12-28 + raw_clarion_days
```

Example:

```text
82123 -> 11/01/2025
```

Show converted dates in diagnostics when possible, not only raw values.

## Review Queries For SQLite

Use these as starting points when a PHDWin SQLite review database is available.

Table inventory:

```sql
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
```

Core row counts:

```sql
SELECT 'PHD_MAINLSE' AS table_name, COUNT(*) AS row_count FROM PHD_MAINLSE
UNION ALL SELECT 'PHD_OWNER', COUNT(*) FROM PHD_OWNER
UNION ALL SELECT 'PHD_GROUPS', COUNT(*) FROM PHD_GROUPS
UNION ALL SELECT 'PHD_LIST', COUNT(*) FROM PHD_LIST
UNION ALL SELECT 'PHD_FORCAST', COUNT(*) FROM PHD_FORCAST
UNION ALL SELECT 'PHD_MONHIST', COUNT(*) FROM PHD_MONHIST;
```

Cases missing ownership:

```sql
SELECT M.LSE_ID, M.LSE_NAME
FROM PHD_MAINLSE M
LEFT JOIN PHD_OWNER O
  ON O.LSE_ID = M.LSE_ID
WHERE O.LSE_ID IS NULL
ORDER BY M.LSE_NAME;
```

Group membership:

```sql
SELECT L.GRP_ID, COUNT(*) AS member_count
FROM PHD_LIST L
GROUP BY L.GRP_ID
ORDER BY L.GRP_ID;
```

Forecast product coverage:

```sql
SELECT PRODUCTCODE, COUNT(*) AS row_count
FROM PHD_FORCAST
GROUP BY PRODUCTCODE
ORDER BY PRODUCTCODE;
```

Filter and sort inventory:

```sql
SELECT 'PHD_FILTER' AS table_name, COUNT(*) AS row_count FROM PHD_FILTER
UNION ALL SELECT 'PHD_FILTERLINE', COUNT(*) FROM PHD_FILTERLINE
UNION ALL SELECT 'PHD_SORT', COUNT(*) FROM PHD_SORT;
```

## Conversion Readiness Memo

When asked to review a PHDWin-to-Aries conversion, return a memo with:

- source path and source type
- whether review used native PHDWin, SQLite, CSV, or Access
- driver/readability status if native files were involved
- core table presence and row counts
- selected lease/project/filter/sort scope
- project membership interpretation
- `AC_PROPERTY` readiness
- ownership readiness
- actuals readiness: `AC_PRODUCT`, `AC_DAILY`, `AC_TEST`
- economics readiness: `AC_ECONOMIC`
- setup/scenario/lookup readiness
- duplicate key or missing join risks
- known limitations and unverified assumptions
- recommended next action

## Red Flags

Call these out explicitly:

- native driver required but missing
- concurrent native driver use
- missing `PHD_MAINLSE`
- missing `PHD_OWNER`
- missing `PHD_FORCAST`
- missing `PHD_MONHIST`
- PHDWin source can be inventoried but cannot be queried
- `PHD_LIST` absent when group/project fidelity is important
- duplicate target keys in any ARIES table
- `AC_PROPERTY` column casing drift
- dynamic Access column names replacing fixed contracts
- template-owned rows being deleted
- `AC_SETUPDATA` being truncated instead of appended
- daily/test rows being misclassified
- group/incremental projects treated as plain folders
- last-used PHDWin UI filter/sort state inferred without evidence

## Output Preference

For public Claude Cowork workflows:

1. SQLite review database first.
2. Named CSV files for inspectable ARIES target tables.
3. Optional Access `.accdb` export from the bundled template when Windows Access ODBC is available.
4. Human review before any ARIES import or mutation.
