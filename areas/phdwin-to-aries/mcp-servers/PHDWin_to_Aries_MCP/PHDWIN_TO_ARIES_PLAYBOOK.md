# PHDWin To Aries Cowork Playbook

This package is for using Claude Cowork as a local analyst for PHDWin-to-Aries conversion review.

The MCP server should be treated as a read-only inspection layer over PHDWin source data. Actual Aries conversion/export should remain in the controlled Tauris.PhdWin workflow.

The Clarion / TopSpeed ODBC driver is only required for the one-time native PHDWin extraction/export step. Once a SQLite review database exists, Cowork can review that SQLite file without the Clarion driver.

Use `PHDWIN_TO_ARIES_TABLE_MAP.md` as the source table semantics guide when reviewing SQLite exports.

Use `reference/` for the deeper Tauris.PhdWin conversion context and bundled Aries Access template. In particular:

- `reference/tauris-phdwin-docs/PHDWIN_DATA_MAP.md`
- `reference/tauris-phdwin-docs/ARIES_ACCESS_TABLE_CONTRACTS.md`
- `reference/tauris-phdwin-docs/ARIES_SCHEMA_MAPPING.md`
- `reference/templates/Aries_Template.accdb`

## ⚠️ Clarion / TopSpeed ODBC Driver Constraint

**Read this before running any conversion or extraction.**

The SoftVelocity Clarion / TopSpeed ODBC driver is fragile and must be treated as a **single-user, serialized resource**.

Do not allow concurrent access to native PHDWin `.phd`, `.mod`, `.tps`, or extracted dataset folders through the driver. The driver can lock files, leave stale locks, fail under overlapping requests, or destabilize the process when multiple reads happen at once.

**Required behavior:**

1. Queue all native PHDWin extraction jobs.
2. Run only one Clarion/TopSpeed ODBC job at a time per machine/process.
3. Keep driver access short-lived.
4. Open the native PHDWin source only long enough to extract/export to SQLite or staged storage.
5. Close every ODBC connection in `finally` / context-manager cleanup.
6. Do not use the driver for repeated analytical queries once SQLite/staged data exists.
7. Perform all deeper Claude/AI review against SQLite or staged database copies.
8. Detect and report stale lock files before retrying.
9. Do not retry aggressively while a lock is present.
10. Prefer an explicit job state model: `Queued → Extracting → Extracted → Reviewing → Failed`.

---

## Goal

For a given PHDWin v2 source package, Cowork should answer:

- Can this source be read locally?
- Are the core PHDWin-to-Aries source tables present?
- Which PHDWin fields should drive Aries property, ownership, forecast, production, economics, filters, sorts, and lookup mapping?
- What looks risky before conversion?
- Should we export a SQLite review copy for repeatable QA?

## Standard Cowork Prompt

```text
Use the phdwin-to-aries MCP server.

Focus only on PHDWin-to-Aries conversion readiness and mapping review.

Source:
C:\Path\To\Client\File.phz

Workflow:
1. Run env_check.
2. Inspect the source.
3. If the source is a .phz or .zip, extract it to a sibling folder.
4. Run conversion_readiness on the extracted dataset folder.
5. Run conversion_profile.
6. Summarize:
   - whether the source is readable
   - required tables present/missing
   - key row counts
   - source tables for Aries AC_PROPERTY
   - source tables for Aries AC_OWNER
   - source tables for Aries AC_ECONOMIC
   - source tables for production/history
   - source tables for filters, sorts, projects, and lookups
   - conversion risks or unknowns
7. Do not modify native PHDWin files.
8. Recommend whether to export a SQLite review copy before deeper QA.
```

## Conversion Source Map

| Aries area | PHDWin source tables |
|---|---|
| `AC_PROPERTY`, `PROJECT`, `PROJLIST` | `PHD_TITLES`, `PHD_MAINLSE`, `PHD_IDCODES`, `PHD_IDLABELS`, `PHD_CLASS`, `PHD_CATEGORY` |
| `AC_OWNER`, `GROUPTEST` | `PHD_OWNER`, `PHD_GROUPS`, `PHD_LIST`, `PHD_ADJOWNER` |
| `AC_PRODUCT`, `AC_DAILY`, `AC_TEST` | `PHD_PRODUCTNAMES`, `PHD_MONHIST`, `PHD_CUMVOL`, possible daily/test source tables when present |
| `AC_ECONOMIC` production forecasts | `PHD_FORCAST`, `PHD_LSESEGMENT`, `PHD_LSEPRODVAL` |
| `AC_ECONOMIC` expenses/capital | `PHD_ECON`, `PHD_INVEST`, `PHD_INVESTDESCR`, `MOD_SCEN`, `MOD_TEMPLATE` |
| `SelFilters`, `SORTFILTERS`, project behavior | `PHD_FILTER`, `PHD_FILTERLINE`, `PHD_SORT`, `PHD_LIST`, `PHD_GROUPS` |
| ARIES lookup context | `PHD_IDCODES`, `PHD_IDLABELS`, `PHD_CLASS`, `PHD_CATEGORY`, `PHD_PRODUCTNAMES` |

## First-Pass Risk Checks

Ask Cowork to inspect these before any conversion run:

- Missing `PHD_MAINLSE`, `PHD_OWNER`, `PHD_FORCAST`, or `PHD_MONHIST`.
- Case/well rows in `PHD_MAINLSE` with no ownership rows.
- Owner/group rows that do not join cleanly.
- Forecast rows with unexpected product codes.
- Missing product name/code definitions.
- Filters/sorts that imply client-specific project membership.
- `PHD_LIST` membership that should drive project/group exports.
- Economic/investment tables present but not sampled.
- Any table required by conversion that is unreadable through ODBC.

## Preferred Review Flow

1. Use native ODBC only long enough to inspect and export.
2. Export selected PHDWin tables to SQLite.
3. Use SQLite for deeper Cowork analysis.
4. Keep Aries conversion/export in Tauris.PhdWin.
5. Treat Cowork output as a review memo, not the source of record.

## Driver Requirement Boundary

```text
Requires Clarion driver:
  .phz / .phd + .mod -> SQLite review database

Does not require Clarion driver:
  SQLite review database -> Cowork readiness/mapping/risk review
```

If the user does not have the Clarion driver, ask for the exported SQLite review database instead of trying to query native PHDWin files.

If the user needs to create the SQLite review database and does not have the Clarion / TopSpeed / SoftVelocity driver, send them here:

```text
https://softvelocity.myshopify.com/
```

## SQLite Export Prompt

```text
Use the phdwin-to-aries MCP server.

Export the PHDWin-to-Aries review tables from:
C:\Path\To\Client\ExtractedDataset

To:
C:\Path\To\Client\review\phdwin_to_aries_review.sqlite

Use overwrite=false unless the file does not exist.
Do not modify native PHDWin files.
```

## Expected Cowork Output

Ask Cowork for a concise memo:

```text
Give me a PHDWin-to-Aries conversion readiness memo with:
- source path
- driver/readability status
- table readiness
- high-signal row counts
- source-to-Aries mapping notes
- conversion risks
- recommended next action
```
