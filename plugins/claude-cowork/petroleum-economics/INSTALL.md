# Petroleum Economics Claude Cowork Plugin

Installs the petroleum economics review skill as a Cowork prompt/context workflow. This plugin is a work in progress and does not require an MCP server.

## Canonical Files

- Area: `areas/petroleum-economics`
- Skill: `areas/petroleum-economics/skills/petroleum-economics-review`
- Setup guide: `areas/petroleum-economics/SME_SETUP_GUIDE.md`

## Install

1. Clone or unpack this repo to:

```text
C:\Dev\tauris-skills
```

2. In Claude Cowork, add the repo or the petroleum economics area as project context when available.

3. Start Cowork with the recommended prompt below and include source economics files as local attachments or local file paths.

## First Prompt

```text
Use the petroleum economics area in this repo. Start with areas/petroleum-economics/skills/petroleum-economics-review/SKILL.md. Review the supplied economics assumptions and outputs, separate source evidence from assumptions, and identify missing ownership, price, tax, forecast, cost, capital, and payout details.
```

## Notes

Use this plugin for system-agnostic review across PHDWin, ARIES, spreadsheets, CSV exports, reserves databases, or written assumptions. Treat outputs as review notes while the plugin matures. Use the PHDWin v2 or ARIES plugins when the work needs system-specific local database inspection.
