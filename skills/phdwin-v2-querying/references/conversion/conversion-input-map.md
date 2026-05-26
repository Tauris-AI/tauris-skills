# PhdWIN Conversion Input Map

## Purpose

This reference links extracted PhdWIN tables to the Tauris conversion and ARIES-preparation workflow.

## Core Idea

The skill should help users answer:

- what extracted table contains the input I care about
- what key identifies the business object
- what related tables must be joined to interpret the input correctly
- whether the data is sufficient for downstream ARIES conversion

## High-Value Input Areas

### Case / Well Identity

- primary table: `{{phd}}\&MAINLSE`
- anchor key: `LSE_ID`
- common context fields:
  - `LSE_NAME`
  - `FLD`
  - `RESERVOIR`
  - `STATE`
  - `OPER`
  - `CASETYPE`

### Ownership

- primary table: `{{phd}}\&OWNER`
- keys: `LSE_ID`, `GRP_ID`, `SEQ`
- useful supporting table: `{{phd}}\&GROUPS`
- conversion relevance:
  - ownership burdens
  - revenue and working interest interpretation
  - partner/group context

### Forecast Inputs

- primary table: `{{phd}}\&FORCAST`
- keys: `LSE_ID`, `ARCSEQ`, `PRODUCTCODE`
- conversion relevance:
  - segment dates
  - decline and rate arrays
  - EUR and remaining volumes
  - product stream interpretation

### Historical Production

- primary table: `{{phd}}\&MONHIST`
- keys: `LSE_ID`, `TYPE`, `YEAR`
- conversion relevance:
  - history support for forecast interpretation
  - production sanity checks

### Investments / Capital

- primary table: `{{phd}}\&INVEST`
- likely anchor: case plus sequence-style keys
- conversion relevance:
  - capital timing and amounts

### Model / Scenario Context

- primary MOD tables:
  - `{{mod}}\&SCEN`
  - `{{mod}}\&MODPRODVAL`
  - `{{mod}}\&MODSEGMENT`
  - `{{mod}}\&TEMPLATE`
- conversion relevance:
  - scenario definitions
  - model variable defaults
  - template/model overlays versus case-specific values

## Key Logic To Explain

The skill should explicitly explain that:

- `LSE_ID` is the main case/well anchor across many `PHD_*` tables
- `GRP_ID` links ownership/group-oriented records
- `FLT_ID` links filter headers to filter lines
- `SRT_ID` identifies saved sort definitions
- `ARCSEQ` distinguishes forecast rows/segments within a case
- `PRODUCTCODE` identifies product/stream rows in forecast and related tables

## Querying For Conversion Readiness

When a user is preparing for ARIES-oriented conversion, the skill should:

1. name the required source tables
2. identify the minimum required keys and fields
3. point out missing related tables
4. distinguish verified mappings from assumptions
5. recommend read-only extraction and review before any mutation/export step
