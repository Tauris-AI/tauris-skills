# Data Workspace

Use this folder for local PHDWin-to-Aries review work.

## Folder Layout

```text
data/
  original/   Put original client files here: .phz, .zip, .phd/.mod packages
  extracted/  Put extracted .phd/.mod dataset folders here
  review/     Put generated SQLite review databases here

reports/      Put Claude/Claude Code readiness memos and mapping notes here
```

## Recommended Flow

1. Drop the original PHDWin file into `data/original/`.
2. If it is a `.phz` or `.zip`, extract it into `data/extracted/<client-or-project-name>/`.
3. Export the review SQLite database to `data/review/<client-or-project-name>_phdwin_to_aries_review.sqlite`.
4. Ask Claude Code to run the PHDWin-to-Aries readiness review against the SQLite file.

## Driver Boundary

Native `.phz`, `.phd`, and `.mod` extraction requires the Clarion / TopSpeed ODBC driver.

Reviewing an existing SQLite database does not require the Clarion driver.
