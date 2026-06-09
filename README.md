# Tauris Skills

Reusable agent skills for Tauris petroleum engineering workflows.

This repository is intended to be the source of truth for curated domain skills that can be adapted for Codex, Claude, GitHub Copilot, and other agent tools. Keep the durable domain knowledge here, then expose it through each tool's preferred packaging format.

## Structure

- `areas/` contains each workflow area, including its skills, MCP servers, setup guide, references, and scripts.
- `plugins/` contains tool-facing install adapters. These are thin wrappers around `areas/`; they should not duplicate durable domain content.
- `.github/copilot-instructions.md` and `.github/prompts/` provide Copilot-facing adapters.
- `docs/` contains curation guidance for keeping the skills accurate and safe.

Use area docs as the canonical source when updating domain behavior. Use plugin docs only to describe how a tool loads or invokes that behavior.

### Repository Map

```text
tauris-skills/
`-- areas/
    |-- aries/                         <-- plugin "aries"
    |   |-- .claude-plugin/plugin.json
    |   |-- skills/
    |   |   |-- aries-core/            SKILL.md + references/
    |   |   `-- aries-ac-economic/     SKILL.md + references/ + scripts/
    |   |-- mcp-servers/aries-mcp/     direct .accdb/.mdb read/write/backup
    |   `-- reference/templates/       aries_access_template.sqlite, README.md
    |
    |-- phdwin-v2/                     <-- plugin "phdwin-v2"
    |   |-- .claude-plugin/plugin.json
    |   |-- skills/phdwin-v2-querying/ SKILL.md + references/ + scripts/ + adapters/ + agents/
    |   `-- mcp-servers/PHDWinv2_MCP/  inspection + conversion + export tools
    |       |-- START_HERE.md
    |       |-- PHDWIN_TO_ARIES_PLAYBOOK.md
    |       |-- PHDWIN_TO_ARIES_TABLE_MAP.md
    |       |-- scripts/               phdwin_mcp_server.py, aries_export.py, ...
    |       |-- data/
    |       `-- reference/
    |           |-- aries-conv-docs/   ARIES_ACCESS_TABLE_CONTRACTS.md, ARIES_AC_PROPERTY_RULES.md,
    |           |                      ARIES_ACCESS_EXPORT_PLAN.md, ARIES_EXPORT_RUNNING_LIST.md,
    |           |                      ARIES_SCHEMA_MAPPING.md, PHDWIN_DATA_MAP.md, ...
    |           `-- phdwin-v2/         Phdwinout definitions_complete.xls
    |
    |-- forecasting/                   <-- plugin "forecasting"
    |   |-- .claude-plugin/plugin.json
    |   |-- skills/auto-forecasting/   SKILL.md
    |   |-- mcp-servers/forecasting-mcp/  + data/
    |   |-- references/
    |   `-- assets/
    |
    `-- petroleum-economics/           <-- plugin "petroleum-economics"
        |-- .claude-plugin/plugin.json
        `-- skills/petroleum-economics-review/  SKILL.md + references/
```

## Areas

- `areas/aries`: ARIES concepts, Access table contracts, economic table review, and ARIES skill setup.
- `areas/forecasting`: production/pressure profiling, forecast origin selection, method eligibility, and auto-forecast QC.
- `areas/phdwin-v2`: PHDWin v2 inspection, extraction, SQLite/CSV review exports, and PHDWin-to-Aries workflow support.
- `areas/petroleum-economics`: repeatable review workflows for petroleum engineering economics.

## Current Skills

- `areas/aries/skills/aries-core`: ARIES concepts, module boundaries, and shared operating rules.
- `areas/aries/skills/aries-ac-economic`: reading, validating, and eventually writing `AC_ECONOMIC` table lines.
- `areas/forecasting/skills/auto-forecasting`: production/pressure data profiling, forecast origin selection, method eligibility, and limited-data QC.
- `areas/phdwin-v2/skills/phdwin-v2-querying`: safe query patterns and schema navigation for PHDWin databases.
- `areas/petroleum-economics/skills/petroleum-economics-review`: repeatable review workflows for petroleum engineering economics.

## MCP Servers

- `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP`: read-only PHDWin v2 inspection, `.phz` extraction, table sampling, SQLite/CSV exports, PHDWin-to-Aries conversion-readiness review, and optional Aries Access export reference material.
- `areas/forecasting/mcp-servers/forecasting-mcp`: production/pressure CSV profiling and per-well forecast method recommendation.

## Testing

Committed smoke tests live under `scripts/` and are run by GitHub Actions:

```bash
python3 scripts/test_forecasting_mcp.py
python3 scripts/test_plugin_integrity.py
```

For local end-to-end testing, use the top-level `e2e-local/` workspace. README files are tracked, but generated files, source databases, SQLite review databases, CSV exports, logs, screenshots, and AI transcripts are ignored:

- `e2e-local/aries/`
- `e2e-local/phdwin-v2/`
- `e2e-local/forecasting/`
- `e2e-local/petroleum-economics/`

Use those folders for Claude Cowork, MCP, and workflow-level tests that need local data or generated artifacts. Keeping E2E workspaces outside `areas/` prevents local test data from being packaged with area/plugin releases.

## Claude Cowork Plugins

- `plugins/claude-cowork/phdwin-v2`: Cowork MCP install guide for PHDWin v2 inspection and PHDWin-to-Aries review.
- `plugins/claude-cowork/aries`: Cowork MCP install guide for ARIES Access inspection plus ARIES skill loading.
- `plugins/claude-cowork/forecasting`: Cowork MCP install guide for production/pressure profiling and forecast method recommendation.
- `plugins/claude-cowork/petroleum-economics`: Cowork prompt-only install guide for system-agnostic petroleum economics review.

Keep plugin guides small. The canonical code, references, and skills stay under `areas/`.

## Safety Rules

Do not commit secrets, passwords, private keys, raw production exports, DSNs, connection strings, license keys, or customer confidential data. Use sanitized schemas, synthetic examples, and environment variable placeholders.

When a workflow writes to an ARIES, PhdWIN, or other production database, the skill must require an explicit dry-run or review step before mutation.

## License

This repository and its release packages are published under the MIT License. See `LICENSE`.
