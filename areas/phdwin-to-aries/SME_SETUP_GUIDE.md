# PHDWin To Aries Area - SME Setup Guide

Lets Claude Cowork review PHDWin-to-Aries conversion readiness, table mapping, group/project behavior, and Aries Access export assumptions.

## Prerequisites

Complete these once per machine.

1. Python 3.10 or newer:

```cmd
python --version
```

2. Python packages:

```cmd
pip install -r C:\Dev\tauris-skills\areas\phdwin-to-aries\mcp-servers\PHDWin_to_Aries_MCP\requirements.txt
```

3. SoftVelocity Clarion / TopSpeed ODBC driver for native PHDWin extraction.

The driver is used to get native PHDWin data into reviewable SQLite/CSV artifacts. Once SQLite exists, review work does not need the driver.

## Register With Claude Cowork

Use Cowork settings, not `%APPDATA%\Claude`.

1. Open Cowork.
2. Open Settings.
3. Go to Developer.
4. Click Edit Config.
5. Add the MCP entry from:

```text
areas/phdwin-to-aries/mcp-servers/PHDWin_to_Aries_MCP/cowork_config.example.json
```

6. Update the Python path if needed:

```cmd
where python
```

7. Fully restart Cowork.

## Included Reference Material

- `PHDWIN_TO_ARIES_PLAYBOOK.md`
- `PHDWIN_TO_ARIES_TABLE_MAP.md`
- `reference/tauris-phdwin-docs`
- `reference/templates/Aries_Template.accdb`

## Usage

Drop source files under:

```text
areas/phdwin-to-aries/mcp-servers/PHDWin_to_Aries_MCP/data/original
```

Use prompts like:

```text
Use the PHDWin-to-Aries area. Inspect this PHDWin source, export review tables if needed, map the source tables to Aries output areas, and produce a conversion-readiness memo.
```

## Scope Boundary

This area supports review and handoff. It does not replace the production conversion/export implementation in `Tauris.PhdWin`.

## Troubleshooting

- Missing PHDWin tables: confirm the export used exact TopSpeed table names from metadata.
- Optional tables missing: note conversion risk; do not fail the whole review automatically.
- Locked SQLite file: restart Cowork or use the included cleanup script.
- Need generic PHDWin inspection only: use `areas/phdwin-v2`.
