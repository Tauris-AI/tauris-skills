# ARIES Local E2E Workspace

Use this folder for local end-to-end ARIES skill and MCP tests.

Everything in this folder is ignored except this README. Good candidates:

- copied `.accdb` / `.mdb` test databases
- backup files created by the ARIES MCP server
- local Cowork transcripts
- generated CSV or SQLite inspection outputs
- screenshots and logs

Suggested smoke flow:

1. Configure the ARIES MCP server from `areas/aries/mcp-servers/aries-mcp/cowork_config.example.json`.
2. Place a cleared local Access test database in this folder.
3. Run an environment check and table inventory through Cowork.
4. Run a read-only sample query.
5. If testing write behavior, confirm the MCP server creates a backup before mutation.
