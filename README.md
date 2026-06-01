# Tauris Skills

Reusable agent skills for Tauris petroleum engineering workflows.

This repository is intended to be the source of truth for curated domain skills that can be adapted for Codex, Claude, GitHub Copilot, and other agent tools. Keep the durable domain knowledge here, then expose it through each tool's preferred packaging format.

## Structure

- `areas/` contains each workflow area, including its skills, MCP servers, setup guide, references, and scripts.
- `.github/copilot-instructions.md` and `.github/prompts/` provide Copilot-facing adapters.
- `docs/` contains curation guidance for keeping the skills accurate and safe.

## Areas

- `areas/aries`: ARIES concepts, Access table contracts, economic table review, and ARIES skill setup.
- `areas/phdwin-v2`: PHDWin v2 inspection, extraction, SQLite/CSV review exports, and PHDWin-to-Aries workflow support.
- `areas/petroleum-economics`: repeatable review workflows for petroleum engineering economics.

## Current Skills

- `areas/aries/skills/aries-core`: ARIES concepts, module boundaries, and shared operating rules.
- `areas/aries/skills/aries-ac-economic`: reading, validating, and eventually writing `AC_ECONOMIC` table lines.
- `areas/phdwin-v2/skills/phdwin-v2-querying`: safe query patterns and schema navigation for PHDWin databases.
- `areas/petroleum-economics/skills/petroleum-economics-review`: repeatable review workflows for petroleum engineering economics.

## MCP Servers

- `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP`: read-only PHDWin v2 inspection, `.phz` extraction, table sampling, SQLite/CSV exports, PHDWin-to-Aries conversion-readiness review, and optional Aries Access export reference material.

## Safety Rules

Do not commit secrets, passwords, private keys, raw production exports, DSNs, connection strings, license keys, or customer confidential data. Use sanitized schemas, synthetic examples, and environment variable placeholders.

When a workflow writes to an ARIES, PhdWIN, or other production database, the skill must require an explicit dry-run or review step before mutation.

## License

This repository and its release packages are published under the MIT License. See `LICENSE`.
