# Tauris Skills

Reusable agent skills for Tauris petroleum engineering workflows.

This repository is intended to be the source of truth for curated domain skills that can be adapted for Codex, Claude, GitHub Copilot, and other agent tools. Keep the durable domain knowledge here, then expose it through each tool's preferred packaging format.

## Structure

- `skills/` contains vendor-neutral skill folders with `SKILL.md`, references, and scripts.
- `plugins/tauris-petroleum/` contains the initial Codex plugin wrapper.
- `.github/copilot-instructions.md` and `.github/prompts/` provide Copilot-facing adapters.
- `marketplace.json` is a repo-local marketplace manifest for the Codex plugin wrapper.
- `docs/` contains curation guidance for keeping the skills accurate and safe.

## Current Skill Areas

- `aries-core`: ARIES concepts, module boundaries, and shared operating rules.
- `aries-ac-economic`: reading, validating, and eventually writing `AC_ECONOMIC` table lines.
- `phdwin-querying`: safe query patterns and schema navigation for PhdWIN databases.
- `petroleum-economics-review`: repeatable review workflows for petroleum engineering economics.

## Planning

See `docs/planning.md` for the current feature backlog, distribution targets, and open questions.

## Safety Rules

Do not commit secrets, passwords, private keys, raw production exports, DSNs, connection strings, license keys, or customer confidential data. Use sanitized schemas, synthetic examples, and environment variable placeholders.

When a workflow writes to an ARIES, PhdWIN, or other production database, the skill must require an explicit dry-run or review step before mutation.
