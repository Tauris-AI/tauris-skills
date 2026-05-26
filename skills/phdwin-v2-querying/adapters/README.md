# Adapters

This folder contains thin agent-specific wrappers for the vendor-neutral `phdwin-v2-querying` skill.

## Design Rule

Keep the core domain knowledge in:

- `SKILL.md`
- `references/`
- `scripts/`

Use adapter files only to describe:

- when a given agent should use the skill
- which reference files it should load first
- any agent-specific prompt or behavior guidance

## Current Adapters

- `claude.md`
- `codex.md`
- `copilot.md`
