# PHDWin v2 Area - SME Setup Guide

Lets Claude Cowork inspect PHDWin v2 source files, build SQLite/CSV review artifacts, and run PHDWin-to-Aries conversion-readiness workflows through the area-local MCP server and skill.

## Prerequisites

Complete these once per machine.

1. Python 3.10 or newer.

For native PHDWin `.phd` / `.mod` extraction, use **32-bit Python 3.12** because the SoftVelocity TopSpeed ODBC driver is typically 32-bit. A 64-bit Python process cannot see or load the 32-bit ODBC driver.

```cmd
py --list
py -3.12-32 --version
```

2. Python packages:

```cmd
py -3.12-32 -m pip install -r C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\requirements.txt
```

3. SoftVelocity Clarion / TopSpeed ODBC driver for native `.phd` / `.mod` extraction.

The driver is only needed for native extraction. If you already have an exported SQLite review database, you do not need the driver for query/review work.

Confirm the 32-bit Python environment can see the driver:

```cmd
py -3.12-32 -c "import pyodbc; print('\n'.join(pyodbc.drivers()))"
```

Look for:

```text
SoftVelocity Topspeed driver Read-Only (*.tps)
```

## Register With Claude Cowork

Use Cowork settings, not `%APPDATA%\Claude`.

1. Open Cowork.
2. Open Settings.
3. Go to Developer.
4. Click Edit Config.
5. Add the MCP entry from:

```text
areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.example.json
```

For native PHDWin extraction with the 32-bit TopSpeed driver, use the driver-override example instead:

```text
areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.with_driver_override.example.json
```

6. Update the Python version flag or driver name if needed based on `py --list` and `pyodbc.drivers()`.

7. Fully restart Cowork.

## Usage

Drop source files under:

```text
areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/data/original
```

Use prompts like:

```text
Use the PHDWin v2 area. Inspect this .phz, list available tables, export a SQLite review database, and summarize the core petroleum economics tables.
```

For conversion review:

```text
Use the PHDWin v2 area. Run the PHDWin-to-Aries workflow against this source, export a SQLite review database, create named CSV files for the mapped Aries tables, and summarize conversion risks. Do not modify native PHDWin files.
```

## Available Workflows

- check environment and ODBC driver
- inspect `.phz`, `.phd`, `.mod`, or SQLite sources
- extract `.phz`
- list tables
- sample rows
- run read-only SQL
- export SQLite or CSV review artifacts
- export PHDWin-to-Aries mapped CSV tables
- optionally create an Aries Access export from the bundled template when Windows Access ODBC is available

## Troubleshooting

- Driver missing: install the 32-bit SoftVelocity Clarion / TopSpeed ODBC driver for native extraction, then run Cowork with `py -3.12-32`.
- SQLite already exists: skip the driver and use SQLite review tools.
- Cowork server not visible: restart Cowork fully after editing config.
- Locked files: close active Cowork sessions or use the included restart script.
