# Aries

ARIES-specific review and table contract material.

## Included Assets

- Skill: `skills/aries-core`
- Skill: `skills/aries-ac-economic`
- MCP server: `mcp-servers/aries-mcp`
- Setup guide: `SME_SETUP_GUIDE.md`
- Copilot prompt: `../../.github/prompts/aries-ac-economic-review.prompt.md`
- Conversion reference docs: `../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs`
- Access template: `../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/Aries_Template.accdb`
- SQLite Access-template copy: `reference/templates/aries_access_template.sqlite`
- SQLite review template: `../phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/aries_review_template.sqlite`

## Scope

This area explains ARIES table expectations and review rules. It also includes a Python `aries-mcp` server for local Cowork inspection and maintenance of ARIES `.accdb` and `.mdb` files.

Production PHDWin-to-Aries export remains in the PHDWin v2 workflow; this area provides agent-facing ARIES guidance, review assets, and Access database tools.

The local SQLite Access-template copy is included so Claude Code, Cowork, and other local agents can inspect the ARIES table/view surface without requiring Access ODBC. It includes SQLite views corresponding to Access query/view objects.
