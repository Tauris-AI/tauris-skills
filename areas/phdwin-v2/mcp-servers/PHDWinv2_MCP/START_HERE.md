# PHDWin v2 MCP

Generic Claude Cowork MCP package for local PHDWin v2 source inspection and SQLite export.

This project intentionally excludes PHDWin-to-Aries conversion playbooks. Use `C:\Dev\tauris-skills\areas\phdwin-to-aries\mcp-servers\PHDWin_to_Aries_MCP` for Aries-specific review.

## Operating Model

```text
PHDWin .phz / .phd + .mod
  -> Clarion / TopSpeed ODBC on one driver-equipped Windows machine
  -> SQLite review database
  -> Cowork / Claude Code review without Clarion
```

The Clarion / TopSpeed / SoftVelocity driver is only required to query native PHDWin files or create SQLite exports.

Driver URL:

```text
https://softvelocity.myshopify.com/
```

## Folders

```text
data/original/   original .phz, .zip, .phd/.mod files
data/extracted/  extracted PHDWin dataset folders
data/review/     generated SQLite databases
reports/         notes and query outputs
```

## Cowork Config

Add this in Cowork Settings -> Developer -> Edit Config:

```json
{
  "mcpServers": {
    "phdwinv2": {
      "command": "py",
      "args": [
        "-3.14",
        "C:/Dev/tauris-skills/areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/scripts/phdwinv2_mcp_server.py"
      ]
    }
  }
}
```

If your Clarion driver is 32-bit only, use a 32-bit Python command instead.

## First Prompt

```text
Use the phdwinv2 MCP server. Run env_check and inspect this source:
C:\Dev\tauris-skills\areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\data\original\example.phz
```

## Tools

- `env_check`
- `inspect_source`
- `extract_phz`
- `list_odbc_drivers`
- `list_tables`
- `get_columns`
- `sample_table`
- `run_select_query`
- `export_sqlite`
- `diagnose_odbc`
