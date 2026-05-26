# PhdWIN Query Patterns

## Defaults

- Use read-only queries unless mutation is explicitly requested and approved.
- Prefer typed endpoints over raw SQL when an existing route answers the question.
- Select only the columns needed for the business question.
- Filter on known keys first: `LSE_ID`, `GRP_ID`, `FLT_ID`, `SRT_ID`, `ARCSEQ`, `PRODUCTCODE`, `YEAR`.
- Include small result sets while exploring unfamiliar schemas.
- Avoid credentials, connection strings, and production paths in prompts, scripts, or committed files.

## Basic SQL Templates

List cases/wells:

```sql
SELECT
  LSE_ID,
  LSE_NAME,
  FLD,
  RESERVOIR,
  STATE,
  OPER,
  CASETYPE
FROM {{phd}}\&MAINLSE
WHERE LSE_ID = ?
```

Get ownership rows for one case:

```sql
SELECT
  LSE_ID,
  GRP_ID,
  SEQ,
  REVTYPE,
  REVVALUE,
  LSENRI,
  WRKINT,
  REVINT,
  NPINT
FROM {{phd}}\&OWNER
WHERE LSE_ID = ?
ORDER BY GRP_ID, SEQ
```

Get historical production rows:

```sql
SELECT
  LSE_ID,
  TYPE,
  YEAR,
  PROD1TD,
  PROD2TD,
  PROD3TD,
  PROD4TD,
  PROD5TD
FROM {{phd}}\&MONHIST
WHERE LSE_ID = ?
ORDER BY YEAR
```

Get forecast rows for a case and stream:

```sql
SELECT
  LSE_ID,
  ARCSEQ,
  PRODUCTCODE,
  SEGMENTDATE$1,
  SEGMENTEND$1,
  Q_BEG$1,
  Q_END$1,
  DECLINE$1,
  EURVOL
FROM {{phd}}\&FORCAST
WHERE LSE_ID = ?
  AND PRODUCTCODE = ?
ORDER BY ARCSEQ
```

Inspect filter definitions:

```sql
SELECT
  F.FLT_ID,
  F.NAME,
  L.SEQNO,
  L.FLTFIELD,
  L.CONDITION,
  L.VALUE
FROM {{phd}}\&FILTER F
JOIN {{phd}}\&FILTERLINE L
  ON F.FLT_ID = L.FLT_ID
WHERE F.FLT_ID = ?
ORDER BY L.SEQNO
```

Inspect sort definitions:

```sql
SELECT
  SRT_ID,
  NAME,
  SORTFIELD$1,
  SORTDIR$1,
  LEVEL$1,
  SORTFIELD$2,
  SORTDIR$2,
  LEVEL$2
FROM {{phd}}\&SORT
WHERE SRT_ID = ?
```

## Endpoint-First Patterns

Use route-level GETs for simple table reads:

- `/api/mainlse` for case inventory
- `/api/groups` for group definitions
- `/api/filter` and `/api/filterline` for saved filters
- `/api/sort` for sort/subtotal definitions
- `/api/owner` for raw ownership rows
- `/api/monhist` for historical production
- `/api/forcast` for raw forecast rows

Use business endpoints when the result should already be shaped:

- `/api/project/<lse_id>`
- `/api/projecttree`
- `/api/projectvariable?lse_id=<id>`
- `/api/forecastvariable/formulas?lse_id=<id>`
- `/api/forecastvariable/segments?lse_id=<id>`
- `/api/ownership?lse_id=<id>`

## Query Review Checklist

- Business question is stated in petroleum-engineering terms.
- The access path is justified: typed endpoint, schema discovery, or raw SQL.
- Tables and joins are named explicitly.
- Key filters are present.
- Array columns use the literal `$n` database names when querying raw SQL.
- Clarion date integers are identified and not silently treated as Gregorian date strings.
- Assumptions and unknowns are listed.
