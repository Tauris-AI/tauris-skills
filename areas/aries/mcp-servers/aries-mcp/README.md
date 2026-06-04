# Aries MCP

Python MCP server for Claude Cowork to inspect and maintain ARIES Access databases.

## Server

- Name: `aries-mcp`
- File: `aries_mcp.py`
- Supported database files: `.accdb`, `.mdb`

## Requirements

- Windows Python visible to Cowork
- `fastmcp`
- `pyodbc`
- Microsoft ACE Access ODBC driver
- Microsoft Access installed for `compact_repair` and `convert_to_accdb`

Install Python packages:

```cmd
py -3.12 -m pip install fastmcp pyodbc
```

## Cowork Config

Merge `cowork_config.example.json` into the Cowork developer MCP config.

```json
{
  "mcpServers": {
    "aries-mcp": {
      "command": "py",
      "args": [
        "-3.12",
        "C:/Dev/tauris-skills/areas/aries/mcp-servers/aries-mcp/aries_mcp.py"
      ]
    }
  }
}
```

Restart Cowork after editing the config.

## Tools

- `list_tables`
- `get_columns`
- `read_table`
- `query`
- `execute`
- `backup_table`
- `setup_import_db`
- `unblock_file`
- `compact_repair`
- `convert_to_accdb`

Use `backup_table` before write tools on production databases.
