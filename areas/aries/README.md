# Aries

ARIES-specific documentation, review, and table contract material.

## Included Assets

- Skill: `skills/aries-core`
- Skill: `skills/aries-ac-economic`
- Optional MCP server: `mcp-servers/aries-mcp`
- Setup guide: `SME_SETUP_GUIDE.md`
- Copilot prompt: `../../.github/prompts/aries-ac-economic-review.prompt.md`
- Conversion reference docs: `../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs`
- Access template: `../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/Aries_Template.accdb`
- SQLite Access-template copy: `reference/templates/aries_access_template.sqlite`
- SQLite review template: `../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/aries_review_template.sqlite`

## Scope

This area is documentation-first. Use it to understand ARIES table expectations, draft or review new `AC_ECONOMIC` lines, and reason about conversion behavior before touching any database.

The Python `aries-mcp` server is optional and only applies when a user supplies a local ARIES `.accdb` or `.mdb` for inspection or maintenance.

Production PHDWin-to-Aries export remains in the PHDWin v2 workflow; this area provides agent-facing ARIES guidance, review assets, and optional Access database tools.

The local SQLite Access-template copy is included only as schema/reference support. It is not required for drafting new documented economic lines.
