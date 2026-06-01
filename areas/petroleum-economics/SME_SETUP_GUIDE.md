# Petroleum Economics Area - SME Setup Guide

Helps Claude Cowork, Codex, or another agent perform system-agnostic petroleum economics review.

This area does not require an MCP server. It is a skill and reference package for reviewing economics from PHDWin, ARIES, spreadsheets, CSV exports, reserves databases, or written assumptions.

## Prerequisites

1. Clone or download this repo.
2. Open the repo folder in your agent tool.
3. Confirm the petroleum economics area exists:

```cmd
dir C:\Dev\tauris-skills\areas\petroleum-economics
```

## Included Skill

- `skills/petroleum-economics-review`

## Recommended Prompt

```text
Use the petroleum economics area in this repo. Start with areas/petroleum-economics/skills/petroleum-economics-review/SKILL.md. Normalize the source material into a system-agnostic economic model, then review assumptions, volumes, pricing, ownership, costs, capital, taxes, groups/projects, and outputs.
```

## Usage

Use this area for:

- reserve and economics sanity checks
- system-agnostic assumption review
- PHDWin vs ARIES economic concept comparison
- price deck and differential review
- ownership and burden review
- capital, LOE, abandonment, and tax review
- NPV/cash-flow/payout reasonableness checks

## Expected Inputs

Any of these can be reviewed:

- CSV exports
- Excel workbooks
- SQLite review tables
- ARIES Access extracts
- PHDWin review exports
- written assumptions
- screenshots or copied tables, when no structured file exists

## Guardrails

- Do not assume table names define business meaning.
- Separate source evidence from reviewer assumptions.
- Mark missing ownership, price, tax, or forecast details as explicit review gaps.
- Keep findings system agnostic unless the user asks for system-specific mapping.
