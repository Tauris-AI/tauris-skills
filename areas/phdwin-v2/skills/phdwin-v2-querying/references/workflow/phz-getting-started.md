# `.phz` Getting Started Guide

Use this guide when the user has a PhdWIN `.phz` file and wants to process it without being a developer.

A `.phz` file is a ZIP archive with a PhdWIN-specific extension. It usually contains a `.Phd` file, a `.MOD` file, and related dataset files. A `.zip` file with the same contents can be handled the same way for testing or transfer.

## Goal

Convert a PhdWIN `.phz` package into a local SQLite database that can be safely queried and analyzed.

Preferred outcome:

```text
source .phz file
  -> local working copy
  -> extracted PhdWIN dataset folder
  -> read-only ODBC smoke test
  -> exported SQLite database
  -> read-only analysis/query workflow
```

## Requirements

The user needs:

- A Windows machine, preferably the same machine where PhdWIN or its data tools are installed.
- The `.phz` file saved to a known local folder.
- Python 3 installed on Windows.
- The `pyodbc` Python package installed in that Windows Python environment.
- The Clarion / TopSpeed ODBC driver installed on Windows.
- Permission to process the client or company data locally.
- A local working folder where extracted files and SQLite output can be written.

Important constraints:

- Do not process the `.phz` directly from an email attachment preview, cloud preview, chat upload preview, or temporary download location.
- Do not upload the `.phz` to ChatGPT, Claude, or another external service unless explicitly approved.
- Do not write back to `.phz`, `.phd`, `.mod`, or `.tps` files.
- Treat the first pass as read-only extraction and verification.

## Recommended Folder Setup

Ask the user to create or choose a working folder such as:

```text
C:\PhdWIN-Work\ClientName\
```

Inside that folder, use this layout:

```text
C:\PhdWIN-Work\ClientName\
  original\
    source-file.phz
  extracted\
  output\
    source-file.sqlite
```

The `original` folder stores the untouched source file.
The `extracted` folder stores the unpacked PhdWIN dataset.
The `output` folder stores SQLite exports and query results.

## Non-Coder Kickoff Flow

Tell the user:

1. Copy or save the `.phz` file into the `original` folder.
2. Open Codex Desktop on the Windows machine that has access to the file.
3. Open the `tauris-skills` repository folder in Codex Desktop.
4. Ask Codex to use this skill and run the local PhdWIN CLI.
5. Provide the full path to the saved `.phz` file.

Example prompt for Codex Desktop:

```text
Use the phdwin-v2-querying skill. I have a PhdWIN .phz file saved here:

C:\PhdWIN-Work\ClientName\original\source-file.phz

Please help me process it locally. First check my environment, then extract the .phz, smoke-test the extracted dataset, and export the standard tables to SQLite. Keep everything read-only.
```

## CLI Steps Codex Should Run

From the skill folder:

```bash
python scripts/phdwin_cli.py env
python scripts/phdwin_cli.py inspect "C:\PhdWIN-Work\ClientName\original\source-file.phz"
python scripts/phdwin_cli.py extract "C:\PhdWIN-Work\ClientName\original\source-file.phz" --out "C:\PhdWIN-Work\ClientName\extracted"
python scripts/phdwin_cli.py smoke "C:\PhdWIN-Work\ClientName\extracted"
python scripts/phdwin_cli.py export-sqlite "C:\PhdWIN-Work\ClientName\extracted" "C:\PhdWIN-Work\ClientName\output\source-file.sqlite"
python scripts/phdwin_cli.py inspect "C:\PhdWIN-Work\ClientName\output\source-file.sqlite"
```

If the environment check fails because `pyodbc` is missing, stop and install `pyodbc` in the Windows Python environment.

If the environment check fails because the Clarion / TopSpeed ODBC driver is missing, stop and install the driver before attempting native PhdWIN extraction.

If running from WSL, do not assume Linux Python can see the Windows ODBC driver. Prefer Windows Python or a Windows-side runner.

## What Success Looks Like

The process is ready for analysis when:

- The `.phz` was extracted to a local dataset folder.
- The extracted folder contains one `.phd` file and optionally one `.mod` file.
- The ODBC smoke test can read core tables.
- A SQLite file exists in the `output` folder.
- `inspect` shows expected `PHD_*` and optional `MOD_*` tables.

At that point, future questions should use the SQLite file first unless the user explicitly needs a fresh export from the native PhdWIN files.

## First Analysis Questions

After SQLite export succeeds, useful first questions are:

- List projects, cases, or wells in the file.
- Show available ownership tables and key columns.
- Find forecast tables and available products/streams.
- Identify production history coverage by well or lease.
- Explain which tables answer a specific business question.

Keep all first-pass analysis read-only.

## Troubleshooting Decision Tree

If `.phz` will not extract:

- Confirm the file was fully copied or downloaded.
- Confirm the path points to the saved local file, not a preview or temporary location.
- Try saving a fresh copy from the source location.

If no `.phd` file appears after extraction:

- Inspect the extracted folder and subfolders.
- Confirm the source file is actually a PhdWIN `.phz` package.
- Ask the sender whether the export was complete.

If ODBC fails:

- Confirm `pyodbc` is installed in the Python environment being used.
- Confirm the Clarion / TopSpeed ODBC driver is installed.
- Confirm the runner is using Windows Python when the driver is Windows-only.
- Confirm the datasource path is the extracted folder, not the `.phz` file.

If SQLite export succeeds but tables are missing:

- Re-run export with explicit table names.
- Inspect available source tables before assuming a business object is absent.
- Note that some datasets may not include optional `.mod` data.
