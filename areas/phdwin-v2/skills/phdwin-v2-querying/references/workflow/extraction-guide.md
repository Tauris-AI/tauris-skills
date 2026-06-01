# PhdWIN V2 Extraction Guide

## Purpose

This reference explains the prerequisites and expected outcome for extracting PhdWIN v2 data into the table surfaces used by the local extraction tooling.

## Driver Requirement

- PhdWIN v2 uses Clarion TopSpeed storage.
- Direct extraction through the supported local implementation requires the Clarion TopSpeed ODBC driver.
- If the user does not have the driver, tell them native extraction cannot proceed until they obtain and install it.
- Do not imply the extraction path is fully supported without that driver.

This driver requirement applies to native PhdWIN source access, not to already-extracted SQLite databases.

## Expected Source Layout

The normal PhdWIN input is an uncompressed dataset folder containing:

- one `.phd` file
- optionally one `.mod` file

The local implementation uses the datasource folder to detect those files and substitute:

- `{{phd}}`
- `{{mod}}`

into the generated table annotations and SQL.

## Extraction Goal

The extraction is successful when the user can:

1. point `datasource` at the uncompressed dataset folder
2. enumerate available tables with `/api/schema`
3. inspect individual table schemas with `/api/schematable`
4. read the important PhdWIN input tables
5. reason about the extracted table names using the local naming conventions

## SQLite Branch

If the user already has extracted SQLite output:

- skip the Clarion driver prerequisite
- verify the SQLite file exists
- verify it opens
- verify the expected extracted tables are present
- continue with read-only lookup guidance

## Expected Extracted Table Families

- `PHD_*` for project/case/history/ownership/filter/sort/forecast style tables
- `MOD_*` for scenario/model/template/value definition tables

These families should be treated as the canonical extracted surfaces for downstream query and conversion work.

## Minimum Extraction Validation

- the datasource path resolves
- the `.phd` file is present
- the driver can open the datasource
- `tables` schema enumeration succeeds
- core tables such as `MAINLSE`, `OWNER`, `GROUPS`, `MONHIST`, and `FORCAST` are readable
- if model/scenario work is needed, `MOD_*` tables are also readable

## User Guidance Pattern

If the user says they cannot open the dataset:

- if the source is `.phz`, `.phd`, or `.mod`, ask whether they have the Clarion TopSpeed ODBC driver
- if the native-source driver is missing, tell them native extraction cannot proceed until they obtain and install it
- if the source is SQLite, skip the driver question and focus on opening the database and checking tables
- if the native-source driver exists, focus on datasource path, `.phd`/`.mod` presence, and schema discovery endpoints
