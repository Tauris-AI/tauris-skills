# PHDWin v2 Area - SME Setup Guide

Lets Claude Cowork inspect PHDWin v2 source files and exported review databases through the area-local MCP server and skill.

## Prerequisites

Complete these once per machine.

1. Python 3.10 or newer:

```cmd
python --version
```

2. Python packages:

```cmd
pip install -r C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\requirements.txt
```

3. SoftVelocity Clarion / TopSpeed ODBC driver for native `.phd` / `.mod` extraction.

The driver is only needed for native extraction. If you already have an exported SQLite review database, you do not need the driver for query/review work.

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

6. Update the Python path if needed. To find it:

```cmd
where python
```

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

## Available Workflows

- check environment and ODBC driver
- inspect `.phz`, `.phd`, `.mod`, or SQLite sources
- extract `.phz`
- list tables
- sample rows
- run read-only SQL
- export SQLite or CSV review artifacts

## Troubleshooting

- Driver missing: install the 32-bit SoftVelocity Clarion / TopSpeed ODBC driver for native extraction.
- SQLite already exists: skip the driver and use SQLite review tools.
- Cowork server not visible: restart Cowork fully after editing config.
- Locked files: close active Cowork sessions or use the included restart script.
