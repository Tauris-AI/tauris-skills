# PhdWIN V2 Extraction Guide

## Purpose

This reference explains the prerequisites and expected outcome for extracting PhdWIN v2 data into the table surfaces used by Tauris tooling.

## Driver Requirement

- PhdWIN v2 uses Clarion TopSpeed storage.
- Direct extraction through `Tauris.PhdWin` requires the Clarion TopSpeed ODBC driver.
- If the user does not have the driver, tell them to contact Tauris AI or SoftVelocity.
- Do not imply the extraction path is fully supported without that driver.

## Expected Source Layout

The normal PhdWIN input is an uncompressed dataset folder containing:

- one `.phd` file
- optionally one `.mod` file

`Tauris.PhdWin` uses the datasource folder to detect those files and substitute:

- `{{phd}}`
- `{{mod}}`

into the generated table annotations and SQL.

## Extraction Goal

The extraction is successful when the user can:

1. point `datasource` at the uncompressed dataset folder
2. enumerate available tables with `/api/schema`
3. inspect individual table schemas with `/api/schematable`
4. read the important PhdWIN input tables
5. reason about the extracted table names using the Tauris naming conventions

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

- ask whether they have the Clarion TopSpeed ODBC driver
- if not, tell them they need it and should contact Tauris AI or SoftVelocity
- if yes, focus on datasource path, `.phd`/`.mod` presence, and schema discovery endpoints
