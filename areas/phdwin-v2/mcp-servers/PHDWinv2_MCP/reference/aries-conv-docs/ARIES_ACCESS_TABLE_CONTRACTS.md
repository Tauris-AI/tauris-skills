# Aries Access Table Contracts

This document is the working contract for writing the final Aries Access `.accdb` export.

Purpose:

- define fixed Aries table names
- define column naming/casing expectations
- define key semantics
- define table-specific ordering rules
- separate raw/internal conversion logic from final Access export rules

## Core Rule

For the final Aries Access export:

- the Aries template `.accdb` is the schema guide
- Taurus export rules override any dynamic/inferred naming
- Aries export table/column names must not be inferred from C# property names or JSON keys

In practice:

- use fixed Aries table names
- use fixed Aries column names
- preserve uppercase naming where required
- preserve underscores where required
- preserve stable column order once confirmed
- preserve explicit key semantics

## Global Export Rules

- Aries table names are fixed and should not drift by source database
- Aries column names should be treated as contract-driven, not dynamic
- Where the user has specified uppercase naming, write uppercase columns
- Where the user has specified a composite key, treat that as the effective uniqueness contract for export validation
- `PROJLIST` ordering must be preserved
- `AC_SETUPDATA` is non-keyed

## Table Contracts

### `AC_PROPERTY`

- Table name: `AC_PROPERTY`
- Naming rule:
  - all columns uppercase
  - no spaces
  - no special characters
  - use underscores where needed
- Key:
  - `DBSKEY`
  - `PROPNUM`
- Notes:
  - `DBSKEY` and `PROPNUM` are keyed items
  - this table should be treated as an explicit contract, not a dynamic dictionary dump
  - see also:
    - ARIES_AC_PROPERTY_RULES.md

### `AC_PRODUCT`

- Table name: `AC_PRODUCT`
- Key:
  - `PROPNUM`
  - `P_DATE`

### `AC_DAILY`

- Table name: `AC_DAILY`
- Key:
  - `PROPNUM`
  - `D_DATE`

### `AC_TEST`

- Table name: `AC_TEST`
- Key:
  - `PROPNUM`
  - `T_DATE`

### `AC_ECONOMIC`

- Table name: `AC_ECONOMIC`
- Key:
  - `PROPNUM`
  - `SECTION`
  - `SEQUENCE`

### `AR_SIDEFILE`

- Table name: `AR_SIDEFILE`
- Key:
  - `FILENAME`
  - `SECTION`
  - `SEQUENCE`

### `ARLOOKUP`

- Table name: `ARLOOKUP`
- Key:
  - `NAME`
  - `LINETYPE`
  - `SEQUENCE`

### `AC_OWNER`

- Table name: `AC_OWNER`
- Key:
  - `PROPNUM`
  - `SCENARIO`
  - `PHASENAME`
  - `STARTDATE`

### `GROUPTEST`

- Table name: `GROUPTEST`
- Key:
  - `Group_Key`
  - `Member`
  - `T_Date`
- Notes:
  - preserve exact casing for keyed columns as specified unless template inspection proves otherwise

### `AC_SCENARIO`

- Table name: `AC_SCENARIO`
- Key:
  - `DBSKEY`
  - `SCEN_NAME`
  - `DATA_SECT`

### `AC_SETUPDATA`

- Table name: `AC_SETUPDATA`
- Key:
  - none
- Notes:
  - non-keyed reference/setup table

### `PROJECT`

- Table name: `PROJECT`
- Key:
  - `PROJE`
  - `PROJKEY`
- Notes:
  - this is a stable Aries table and should not drift between exports

### `PROJLIST`

- Table name: `PROJLIST`
- Key:
  - `PROJKEY`
  - `PROJSEQ`
- Notes:
  - do not change row order
  - preserve table order semantics during export

## Implementation Guidance

The Aries Access writer should eventually use this document plus template inspection as its source of truth.

Recommended writer behavior:

1. Read the template table structure.
2. Apply Taurus table-specific overrides from this document.
3. Build explicit export column lists per table.
4. Map source data into those exact target columns.
5. Validate duplicates against the declared key contract before insert where practical.
6. Preserve ordering rules for tables like `PROJLIST`.

## Current Gaps

Still to be confirmed or added later:

- explicit full column lists per table
- explicit column ordering per table
- which indexes/constraints from the Aries template should be recreated
- whether any additional Aries tables need contract definitions
