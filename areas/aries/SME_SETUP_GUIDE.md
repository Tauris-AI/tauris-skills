# ARIES Area - SME Setup Guide

Helps Claude Cowork, Codex, or another agent review ARIES concepts, draft new `AC_ECONOMIC` lines from documentation, and review Access-export assumptions using the area-local skills.

## Prerequisites

Complete these once per machine or workspace.

1. Clone or download this repo.
2. Open the repo folder in your agent tool.
3. Confirm the ARIES area exists:

```cmd
dir C:\Dev\tauris-skills\areas\aries
```

## Included Skills

- `skills/aries-core`
- `skills/aries-ac-economic`

## Default Use: Documentation First

For AC_ECONOMIC line work, start with:

- `skills/aries-core/SKILL.md`
- `skills/aries-ac-economic/SKILL.md`
- `skills/aries-ac-economic/references/aries-ac-economic-best-practices.md`
- `skills/aries-ac-economic/references/ac-economic-line-grammar.md`
- `skills/aries-ac-economic/references/ac-economic-calculations.md`
- `skills/aries-ac-economic/references/ac-economic-keyword-catalog.md`
- `skills/aries-ac-economic/references/line-format.md`
- `skills/aries-ac-economic/references/validation-rules.md`
- `skills/aries-ac-economic/references/phdwin-ac-economic-resolver.md` when the task involves the Python MCP exporter or PHDWin source-table parsing

This path does not require an ARIES database. Use it for creating proposed new lines, reviewing assumptions, and preparing dry-run edits.

## Optional Cowork MCP Server

Configure this only for local ARIES Access database inspection:

- `mcp-servers/aries-mcp`

The server name is `aries-mcp`, and the Python entrypoint is:

```text
areas/aries/mcp-servers/aries-mcp/aries_mcp.py
```

It supports both `.accdb` and `.mdb` paths through the Microsoft ACE Access ODBC driver. It is not required for documentation review or drafting new lines.

Use the example config:

```text
areas/aries/mcp-servers/aries-mcp/cowork_config.example.json
```

## Recommended Prompt

```text
Use the ARIES area in this repo. Start with areas/aries/skills/aries-core/SKILL.md and areas/aries/skills/aries-ac-economic/SKILL.md. For AC_ECONOMIC line work, read references/aries-ac-economic-best-practices.md, references/ac-economic-line-grammar.md, references/ac-economic-calculations.md, references/ac-economic-keyword-catalog.md, references/line-format.md, and references/validation-rules.md first. For PHDWin-to-ARIES Python exporter behavior, also read references/phdwin-ac-economic-resolver.md. Draft proposed new lines as a dry-run artifact. Do not ask for a database unless I specifically request inspection of a supplied `.accdb`, `.mdb`, or SQLite export.
```

## Usage

Use this area for:

- ARIES table concepts
- drafting proposed `AC_ECONOMIC` lines from documented assumptions
- ARIES `.accdb` / `.mdb` inspection through the optional MCP server
- `AC_ECONOMIC` review
- economic-line validation rules
- dry-run change planning
- explaining how ARIES concepts relate to PHDWin conversion review

## Guardrails

- Do not write directly to ARIES without explicit approval.
- Use scrubbed or synthetic examples in public artifacts.
- Keep conversion/export implementation in `Tauris.PhdWin`.
- Use the PHDWin v2 area when the task depends on source PHDWin data or PHDWin-to-Aries conversion review.

## Troubleshooting

- If the agent cannot find the skill, point it to `areas/aries/skills`.
- If the task involves PHDWin source files, switch to `areas/phdwin-v2`.
- If the task is general petroleum economics, switch to `areas/petroleum-economics`.
