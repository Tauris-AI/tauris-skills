# PHDWin To Aries Table Map

Use this map when reviewing a SQLite database exported from PHDWin v2 source files.

The SQLite table names should generally preserve the logical names below, such as `PHD_MAINLSE`, `PHD_OWNER`, and `PHD_FORCAST`.

## Core Mapping

| Aries target area | PHDWin source table | Role in review |
|---|---|---|
| Project/header | `PHD_TITLES` | Project name, group/default context, effective/as-of signals when present |
| Property/case identity | `PHD_MAINLSE` | Core case/well rows; lease/case ID, name, location, operator, reserve class/category fields |
| Product names | `PHD_PRODUCTNAMES` | Product code labels used by forecast/history/economic rows |
| Ownership | `PHD_OWNER` | WI/NRI/revenue interest rows by case/group/sequence |
| Ownership groups | `PHD_GROUPS` | Group/partner definitions and project/group labels |
| Project/group membership | `PHD_LIST` | Explicit list membership for project/group style exports when present |
| Adjusted ownership | `PHD_ADJOWNER` | Adjusted ownership rows; review when ownership does not reconcile |
| Forecasts | `PHD_FORCAST` | Forecast rows and segment arrays; preserve misspelling `FORCAST` |
| Lease/product values | `PHD_LSEPRODVAL` | Case-specific product/value overrides |
| Lease segments | `PHD_LSESEGMENT` | Case-specific segment/expense/forecast detail |
| Monthly history | `PHD_MONHIST` | Monthly or annualized historical production rows |
| Cumulative volumes | `PHD_CUMVOL` | Cumulative forecast/history volume context |
| Economics | `PHD_ECON` | Economic assumptions by case/project when present |
| Investments | `PHD_INVEST` | Capital/investment rows |
| Investment descriptions | `PHD_INVESTDESCR` | Labels/descriptions for investment rows |
| Scenario/model economics | `MOD_SCEN` | Model/scenario assumptions from `.mod` source |
| Templates | `MOD_TEMPLATE` | Model templates and assumptions from `.mod` source |
| Filters | `PHD_FILTER` | Saved filter headers; project/seller view context |
| Filter lines | `PHD_FILTERLINE` | Filter criteria/rules |
| Sorts/subtotals | `PHD_SORT` | Sort/subtotal definitions and grouping behavior |
| Reserve class lookup | `PHD_CLASS` | Reserve class definitions |
| Reserve category lookup | `PHD_CATEGORY` | Reserve category definitions |
| ID code lookup | `PHD_IDCODES` | Code values for field, operator, basin, category, custom IDs, etc. |
| ID label lookup | `PHD_IDLABELS` | Labels/meaning for ID code columns |

## Aries Output Areas

| Aries output area | Primary PHDWin sources |
|---|---|
| `AC_PROPERTY` | `PHD_MAINLSE`, `PHD_TITLES`, `PHD_IDCODES`, `PHD_IDLABELS`, `PHD_CLASS`, `PHD_CATEGORY` |
| `AC_OWNER`, `GROUPTEST` | `PHD_OWNER`, `PHD_GROUPS`, `PHD_LIST`, `PHD_ADJOWNER` |
| `AC_PRODUCT` | `PHD_PRODUCTNAMES`, `PHD_FORCAST`, `PHD_MONHIST` |
| `AC_DAILY`, `AC_TEST` | `PHD_MONHIST`, `PHD_CUMVOL`, daily/test source tables when present |
| `AC_ECONOMIC` production section | `PHD_FORCAST`, `PHD_LSESEGMENT`, `PHD_LSEPRODVAL` |
| `AC_ECONOMIC` expense/capital/economic assumptions | `PHD_ECON`, `PHD_INVEST`, `PHD_INVESTDESCR`, `MOD_SCEN`, `MOD_TEMPLATE` |
| `PROJECT`, `PROJLIST` | `PHD_TITLES`, `PHD_GROUPS`, `PHD_LIST`, `PHD_FILTER`, `PHD_SORT` |
| `SelFilters`, `SORTFILTERS` | `PHD_FILTER`, `PHD_FILTERLINE`, `PHD_SORT`, `PHD_LIST`, `PHD_GROUPS` |
| `ARLOOKUP`, sidefile/lookup context | `PHD_IDCODES`, `PHD_IDLABELS`, `PHD_PRODUCTNAMES`, `PHD_CLASS`, `PHD_CATEGORY` |

## Key Join Anchors

| Business object | Common key fields |
|---|---|
| Case/well | `LSE_ID` |
| Ownership group | `GRP_ID` |
| Ownership row order | `SEQ` |
| Forecast arc/segment | `LSE_ID`, `ARCSEQ`, `PRODUCTCODE` |
| Monthly history | `LSE_ID`, `TYPE`, `YEAR` |
| Filter | `FLT_ID` |
| Sort | `SRT_ID` |

## Review Queries

### Table Inventory

```sql
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
```

### Core Row Counts

```sql
SELECT 'PHD_MAINLSE' AS table_name, COUNT(*) AS row_count FROM PHD_MAINLSE
UNION ALL SELECT 'PHD_OWNER', COUNT(*) FROM PHD_OWNER
UNION ALL SELECT 'PHD_GROUPS', COUNT(*) FROM PHD_GROUPS
UNION ALL SELECT 'PHD_FORCAST', COUNT(*) FROM PHD_FORCAST
UNION ALL SELECT 'PHD_MONHIST', COUNT(*) FROM PHD_MONHIST;
```

### Cases Missing Ownership

```sql
SELECT M.LSE_ID, M.LSE_NAME
FROM PHD_MAINLSE M
LEFT JOIN PHD_OWNER O
  ON O.LSE_ID = M.LSE_ID
WHERE O.LSE_ID IS NULL
ORDER BY M.LSE_NAME;
```

### Forecast Product Coverage

```sql
SELECT PRODUCTCODE, COUNT(*) AS row_count
FROM PHD_FORCAST
GROUP BY PRODUCTCODE
ORDER BY PRODUCTCODE;
```

### Filter And Sort Inventory

```sql
SELECT 'PHD_FILTER' AS table_name, COUNT(*) AS row_count FROM PHD_FILTER
UNION ALL SELECT 'PHD_FILTERLINE', COUNT(*) FROM PHD_FILTERLINE
UNION ALL SELECT 'PHD_SORT', COUNT(*) FROM PHD_SORT;
```

## Review Notes

- Preserve the source spelling `PHD_FORCAST`.
- Do not assume all client databases use every table.
- Missing optional tables should be noted, not automatically treated as fatal.
- Missing core tables such as `PHD_MAINLSE`, `PHD_OWNER`, `PHD_FORCAST`, or `PHD_MONHIST` should be treated as conversion risk.
- Filters, sorts, and `PHD_LIST` may be critical for preserving seller/project views in Aries.
- Use SQLite for deeper analysis after the initial driver-based export.
