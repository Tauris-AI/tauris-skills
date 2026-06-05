# Aries Cowork Conversion Inventory

## Purpose

This document records where the PHDWin-to-Aries conversion workflow lives in the Cowork MCP package.

The working conclusion is:

- use the Python Cowork conversion path for public/local review workflows
- keep native PHDWin extraction read-only and serialized
- convert from a stable SQLite review database into Aries-named CSV files
- write an Aries `.accdb` only when Windows Python, `pyodbc`, the Microsoft Access ODBC driver, and a cleared Aries template are available
- treat older C# implementation code as external implementation reference, not as bundled Cowork runtime content

## Runtime Entry Points

### MCP Server

Primary file:

- `scripts/phdwin_mcp_server.py`

Primary tools for the conversion workflow:

- `env_check`
- `inspect_source`
- `extract_phz`
- `conversion_readiness`
- `conversion_profile`
- `export_sqlite`
- `export_table_csvs`
- `convert_to_aries_sqlite`
- `export_aries_to_csv`
- `export_aries_to_accdb`
- `run_select_query`

Primary MCP resources:

- `phdwin://aries-conversion-map`
- `phdwin://aries-review-guide`

### Direct Python CLI

Primary file:

- `scripts/aries_export.py`

Direct command shape:

```bash
python scripts/aries_export.py <source.sqlite> <output-dir>
```

Optional Access export:

```bash
python scripts/aries_export.py <source.sqlite> <output-dir> --accdb <output.accdb>
```

Optional lease-scoped export:

```bash
python scripts/aries_export.py <source.sqlite> <output-dir> --lease-id 123 --lease-id 456
```

`--accdb` requires Windows Access ODBC support. CSV output does not.

## Cowork Conversion Flow

Preferred workflow:

```text
PHDWin .phz / .phd + .mod
  -> extract_phz if packaged
  -> export_sqlite through one serialized Clarion / TopSpeed ODBC read
  -> conversion_readiness and conversion_profile against SQLite
  -> convert_to_aries_sqlite for batched Aries conversion
  -> export_aries_to_csv for Aries-named review tables
  -> optional export_aries_to_accdb using the packaged Aries template
```

Once SQLite exists, do deeper analysis from SQLite rather than repeatedly querying native PHDWin through the Clarion driver.

## Current Python Conversion Surface

`scripts/aries_export.py` currently builds these Aries target tables:

- `AC_PROPERTY`
- `AC_PRODUCT`
- `AC_TEST`
- `AC_DAILY`
- `AC_ECONOMIC`
- `ARLOOKUP`
- `AR_SIDEFILE`
- `AC_OWNER`
- `GROUPTEST`
- `AC_SCENARIO`
- `AC_SETUPDATA`
- `PROJECT`
- `PROJLIST`
- `SORTFILTERS`
- `SelFilters`

Output artifacts:

- one CSV per Aries target table under `<output-dir>/csv`
- `aries-export-summary.json`
- optional `.accdb` copied from an external cleared `Aries_Template.accdb` and populated through Access ODBC

## Core Source Tables

Required or high-signal PHDWin source tables:

- `PHD_TITLES`
- `PHD_MAINLSE`
- `PHD_OWNER`
- `PHD_GROUPS`
- `PHD_PRODUCTNAMES`
- `PHD_FORCAST`
- `PHD_MONHIST`

Recommended source tables for fuller fidelity:

- `PHD_LIST`
- `PHD_ADJOWNER`
- `PHD_FILTER`
- `PHD_FILTERLINE`
- `PHD_SORT`
- `PHD_CLASS`
- `PHD_CATEGORY`
- `PHD_IDCODES`
- `PHD_IDLABELS`
- `PHD_LSEPRODVAL`
- `PHD_LSESEGMENT`
- `PHD_CUMVOL`
- `PHD_INVEST`
- `PHD_INVESTDESCR`
- `PHD_ECON`
- `MOD_SCEN`
- `MOD_TEMPLATE`

## Guardrails

- Do not mutate native PHDWin `.phd`, `.mod`, `.tps`, or `.phz` inputs.
- Do not run concurrent native Clarion / TopSpeed extraction jobs.
- Use SQLite as the repeatable review contract after extraction.
- Do not claim `.accdb` export is available unless Access ODBC prerequisites are present.
- Do not copy vendor help/manual content into the public Cowork package.
- Do not bundle C# implementation snapshots in this Python MCP package.

## Reference Role Of External C# Code

External C# codebases may remain useful for:

- checking intended conversion behavior
- comparing resolved Aries table semantics
- validating Access export expectations
- identifying gaps in the Python Cowork conversion

They should not be presented as the runtime path for this MCP package or copied into `reference/`. For Cowork users, the runtime path is the Python MCP server and `scripts/aries_export.py`.
