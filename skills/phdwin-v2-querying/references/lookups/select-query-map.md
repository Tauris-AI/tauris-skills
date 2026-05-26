# Select Query Map

## Purpose

This reference turns prior Tauris extraction and conversion knowledge into read-only lookup guidance.

The goal is to answer questions such as:

- where is the list of projects or cases
- where is ownership stored for a well
- where do forecast inputs live
- what table contains initial decline inputs for oil for a given well
- what keys link the relevant records together

Keep answers read-only. Express them as table maps, joins, endpoint calls, or `SELECT` logic.

## Core Lookup Anchors

### Projects / Cases / Wells

- primary table: `{{phd}}\&MAINLSE`
- anchor key: `LSE_ID`
- common descriptive fields:
  - `LSE_NAME`
  - `FLD`
  - `RESERVOIR`
  - `STATE`
  - `OPER`
  - `CASETYPE`

Typical lookup shape:

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
ORDER BY LSE_NAME
```

### Ownership

- primary table: `{{phd}}\&OWNER`
- supporting table: `{{phd}}\&GROUPS`
- keys: `LSE_ID`, `GRP_ID`, `SEQ`

Typical lookup shape:

```sql
SELECT
  O.LSE_ID,
  O.GRP_ID,
  G.GRP_DESC,
  O.SEQ,
  O.REVTYPE,
  O.REVVALUE,
  O.LSENRI,
  O.WRKINT,
  O.REVINT,
  O.NPINT
FROM {{phd}}\&OWNER O
LEFT JOIN {{phd}}\&GROUPS G
  ON O.GRP_ID = G.GRP_ID
WHERE O.LSE_ID = ?
ORDER BY O.GRP_ID, O.SEQ
```

### Forecast Inputs

- primary table: `{{phd}}\&FORCAST`
- keys: `LSE_ID`, `ARCSEQ`, `PRODUCTCODE`
- forecast arrays live directly on this table with `$n` column suffixes

Typical lookup shape:

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
  N_FACTOR$1,
  EURVOL
FROM {{phd}}\&FORCAST
WHERE LSE_ID = ?
  AND PRODUCTCODE = ?
ORDER BY ARCSEQ
```

Interpretation note:

- the initial decline rate for a stream is typically looked up from the earliest relevant forecast segment fields such as `DECLINE$1`, with context from `SEGMENTDATE$1`, `Q_BEG$1`, and `Q_END$1`
- preserve the exact source spelling `FORCAST`

### Historical Production

- primary table: `{{phd}}\&MONHIST`
- keys: `LSE_ID`, `TYPE`, `YEAR`

Typical lookup shape:

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

### Filters And Sorts

- filter header: `{{phd}}\&FILTER`
- filter lines: `{{phd}}\&FILTERLINE`
- sorts: `{{phd}}\&SORT`
- keys: `FLT_ID`, `SRT_ID`

## SQLite Guidance

If the PhdWIN data has already been extracted into SQLite:

- keep the same logical table names where Tauris preserved them
- keep the same key logic
- translate the answer into SQLite-safe `SELECT` statements
- do not introduce PostgreSQL-specific syntax

## Working Rule

When older ARIES-conversion work contains useful extraction logic:

- reuse the table and field knowledge
- strip out export and mutation steps
- return a read-only lookup path only
