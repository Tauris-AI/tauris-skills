# ARIES Local E2E Workspace

Use this folder for local end-to-end ARIES skill and MCP tests.

Everything in this folder is git-ignored except this README and the committed
fixtures listed below. Good local-only candidates:

- copied `.accdb` / `.mdb` test databases
- backup files created by the ARIES MCP server
- local Cowork transcripts
- generated CSV or SQLite inspection outputs
- screenshots and logs

## Committed fixtures

ARIES Access databases committed so the area runner has data offline:

- `SampleAriesClassic.accdb` — sample ARIES Classic Access database read by
  `run_aries_e2e.py` for the table inventory and read-only query smoke tests.
- `Aries_Template.accdb` — empty ARIES Access template used as the target for
  `.accdb` export writes (also shared by the phdwin-v2 runner).

Note: these binaries carry their original underlying data; treat as demo/test
material. Generated artifacts (`output/`, `__pycache__/`) remain git-ignored.

Suggested smoke flow:

1. Configure the ARIES MCP server from `areas/aries/mcp-servers/aries-mcp/cowork_config.example.json`.
2. Place a cleared local Access test database in this folder.
3. Run an environment check and table inventory through Cowork.
4. Run a read-only sample query.
5. If testing write behavior, confirm the MCP server creates a backup before mutation.
