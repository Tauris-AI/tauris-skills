# ARIES Claude Cowork Plugin

Installs the optional ARIES MCP server for Claude Cowork and points Cowork at the ARIES skills.

## Canonical Files

- Area: `areas/aries`
- Skills: `areas/aries/skills/aries-core` and `areas/aries/skills/aries-ac-economic`
- MCP server: `areas/aries/mcp-servers/aries-mcp`
- Cowork config: `areas/aries/mcp-servers/aries-mcp/cowork_config.example.json`

## Install

1. Clone or unpack this repo to:

```text
C:\Dev\tauris-skills
```

2. Install Python packages for the ARIES MCP server:

```cmd
py -3.12 -m pip install fastmcp pyodbc
```

3. Confirm the Microsoft Access ODBC driver is visible to the same Python:

```cmd
py -3.12 -c "import pyodbc; [print(d) for d in pyodbc.drivers()]"
```

4. Open Claude Cowork -> Settings -> Developer -> Edit Config.

5. Merge the `aries-mcp` entry from:

```text
C:\Dev\tauris-skills\areas\aries\mcp-servers\aries-mcp\cowork_config.example.json
```

6. Fully restart Claude Cowork.

## First Prompt

```text
Use the ARIES area in this repo. Load areas/aries/skills/aries-core/SKILL.md and areas/aries/skills/aries-ac-economic/SKILL.md, then inspect the supplied ARIES Access database through aries-mcp without writing changes.
```

## Notes

The ARIES MCP server is for local `.accdb` / `.mdb` inspection. Any write or maintenance action should start with an explicit dry-run plan.
