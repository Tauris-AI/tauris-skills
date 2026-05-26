# PhdWIN Schema Notes

This reference is grounded in the checked-in generated entities and server code under `/mnt/c/Dev/Tauris.PhdWin`.

## Core Naming Rules

- Generated entity annotations are the canonical schema source.
- PHD tables use `{{phd}}\&TABLE_NAME`.
- MOD tables use `{{mod}}\&TABLE_NAME`.
- Placeholder resolution depends on the `datasource` folder contents.
- The source table name `FORCAST` is intentionally misspelled and must remain spelled that way in SQL and annotations.

## Core Domains And Anchor Tables

### Cases / Wells

- Table: `{{phd}}\&MAINLSE`
- Entity: `MainlseEntity`
- Route: `/api/mainlse`
- Primary anchor: `LSE_ID`
- Common columns:
  - `LSE_NAME`
  - `FLD`
  - `RESERVOIR`
  - `STATE`
  - `OPER`
  - `WELL`
  - `CASETYPE`
  - `RSV_CLASS`
  - `PDP_CATEGORY`
  - `SOP`
  - `EOP`

### Ownership

- Table: `{{phd}}\&OWNER`
- Entity: `OwnerEntity`
- Route: `/api/owner`
- Common keys:
  - `LSE_ID`
  - `GRP_ID`
  - `SEQ`
- Common columns:
  - `REVTYPE`
  - `REVVALUE`
  - `LSENRI`
  - `WRKINT`
  - `REVINT`
  - `NPINT`
  - `RESOLVEDDATE`

### Groups / Partners

- Table: `{{phd}}\&GROUPS`
- Entity: `GroupsEntity`
- Route: `/api/groups`
- Primary anchor: `GRP_ID`
- Common columns:
  - `GRP_DESC`
  - `NUMLEASES`
  - `OWNER_DEFAULT`
  - `ROY_DEFAULT`

### Filters

- Header table: `{{phd}}\&FILTER`
- Line table: `{{phd}}\&FILTERLINE`
- Entities: `FilterEntity`, `FilterlineEntity`
- Routes: `/api/filter`, `/api/filterline`
- Common join: `FILTER.FLT_ID = FILTERLINE.FLT_ID`
- Useful columns:
  - `NAME`
  - `SEQNO`
  - `FLTFIELD`
  - `CONDITION`
  - `VALUE`

### Sorts

- Table: `{{phd}}\&SORT`
- Entity: `SortEntity`
- Route: `/api/sort`
- Primary anchor: `SRT_ID`
- Important behavior:
  - array columns such as `SORTFIELD$1`, `SORTDIR$1`, `LEVEL$1`
  - repeated definitions continue through `$11`

### Historical Production

- Table: `{{phd}}\&MONHIST`
- Entity: `MonhistEntity`
- Route: `/api/monhist`
- Common keys:
  - `LSE_ID`
  - `TYPE`
  - `YEAR`
- Important behavior:
  - monthly arrays exist as `PROD1$1` through `PROD5$12`
  - total-to-date columns include `PROD1TD` through `PROD5TD`

### Forecast

- Table: `{{phd}}\&FORCAST`
- Entity: `ForcastEntity`
- Route: `/api/forcast`
- Common keys:
  - `LSE_ID`
  - `ARCSEQ`
  - `PRODUCTCODE`
- Important behavior:
  - segment arrays: `SEGMENTDATE$1..10`, `SEGMENTEND$1..10`
  - decline arrays: `Q_BEG$1..10`, `Q_END$1..10`, `DECLINE$1..10`, `N_FACTOR$1..10`
  - variable arrays: `NUMFORM$1..100`, `VALUETYPE$1..100`, `PCODE$1..100`, `VALUEREAL$1..100`, `DATEVAL$1..100`
  - Clarion date integers appear in `SEGMENTDATE`, `SEGMENTEND`, `DATEOFBALANCE`, and `DATEVAL`

## Higher-Level Repo Surface

The repo also exposes shaped business endpoints beyond raw table reads:

- project tree and filtered project tree
- project entity and project variables
- forecast formulas, segments, and parameters
- ownership summaries

Use these when the question is about business meaning rather than literal table content.

## Querying Quirks

- The server requires the `datasource` header and derives `.phd` and `.mod` file names from that folder.
- A dataset folder without a `.phd` file is invalid for the PhdWIN query path.
- Array-backed columns in the generated entities correspond to literal `$n` column names in the source tables.
- Clarion dates are stored as integers and only converted in not-mapped helper properties on the .NET side.
- The ODBC driver is fragile enough that schema discovery endpoints are safer than aggressive ad hoc SQL during exploration.

## Related Repo Evidence

- `README.md` documents datasource handling, raw query usage, and entity/table annotation conventions.
- `docs/PHDWIN_DATA_MAP.md` provides a broader logical crosswalk between PhdWIN mnemonics and logical tables.
- `src/Tauris.Odbc.Common.Objects/GeneratedEntities/*.cs` is the best checked-in source of table names, routes, and column shapes.
