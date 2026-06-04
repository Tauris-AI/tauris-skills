# PHDWin v2 Claude Cowork Plugin

Installs the PHDWin v2 MCP server for Claude Cowork.

## Canonical Files

- Area: `areas/phdwin-v2`
- MCP server: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP`
- Start guide: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/START_HERE.md`
- Cowork config: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.example.json`
- Driver override config: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.with_driver_override.example.json`

## Install

1. Clone or unpack this repo to:

```text
C:\Dev\tauris-skills
```

2. Install the Python packages in the Windows Python environment Cowork will launch:

```cmd
py -3.12-32 -m pip install -r C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\requirements.txt
```

3. For native `.phd` / `.mod` extraction, confirm the 32-bit SoftVelocity TopSpeed ODBC driver is visible:

```cmd
py -3.12-32 -c "import pyodbc; [print(d) for d in pyodbc.drivers()]"
```

4. Open Claude Cowork -> Settings -> Developer -> Edit Config.

5. Merge the `phdwin-v2` entry from:

```text
C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\cowork_config.example.json
```

Use `cowork_config.with_driver_override.example.json` when the driver name must be pinned.

6. Fully restart Claude Cowork.

## First Prompt

```text
Use the phdwin-v2 MCP server. Run env_check and tell me whether this machine is ready to inspect PHDWin v2 sources and create SQLite review artifacts.
```

## Notes

The Clarion / TopSpeed driver is only needed to create SQLite review databases from native PHDWin files. Once a SQLite review database exists, Cowork can inspect and convert review artifacts without the driver.
