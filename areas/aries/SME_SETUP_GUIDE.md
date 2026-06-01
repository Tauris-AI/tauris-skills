# ARIES Area - SME Setup Guide

Helps Claude Cowork, Codex, or another agent review ARIES concepts, `AC_ECONOMIC` line behavior, and Access-export assumptions using the area-local skills.

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

## Recommended Prompt

```text
Use the ARIES area in this repo. Start with areas/aries/skills/aries-core/SKILL.md and areas/aries/skills/aries-ac-economic/SKILL.md. Review the provided ARIES economic data or assumptions. Keep the work read-only unless I explicitly approve a dry-run mutation plan.
```

## Usage

Use this area for:

- ARIES table concepts
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
