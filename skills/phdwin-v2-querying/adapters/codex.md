# Codex Adapter

Use this adapter when exposing `phdwin-v2-querying` to Codex or Codex-compatible skill loaders.

## Purpose

Codex should use the core skill to:

- walk users through PhdWIN v2 extraction prerequisites
- confirm Clarion TopSpeed driver requirements
- explain the extracted table layout used by Tauris workflows
- map business questions onto `PHD_*` and `MOD_*` tables
- explain keys and join logic
- draft safe read-only query paths
- support PhdWIN-to-ARIES preparation

## Core Files

Always start with:

1. `SKILL.md`

Then load by task:

- extraction and setup:
  - `references/workflow/extraction-guide.md`
  - `references/workflow/api-endpoints.md`
- querying:
  - `references/workflow/query-patterns.md`
  - `references/schema/schema-notes.md`
- table/route inspection:
  - `references/schema/generated-entity-map.md`
- conversion prep:
  - `references/conversion/conversion-input-map.md`
- broader domain interpretation:
  - `references/source-library/reference-inputs-index.md`

## Codex Instructions

- Use the skill progressively. Do not load every reference file unless the task needs it.
- Anchor table names and routes in the checked-in generated entities and server code first.
- Explicitly separate verified facts from inferred guidance.
- When the user is pre-extraction, prioritize driver/setup guidance over query examples.
- When the user already has extracted tables, prioritize table purpose, keys, joins, and read-safe access paths.
- When the task is conversion-oriented, explain which PhdWIN tables and keys matter for downstream ARIES logic.

## Behavioral Rules

- If the Clarion TopSpeed ODBC driver is missing, state that direct extraction requires it and direct the user to Tauris AI or SoftVelocity.
- Do not invent unsupported mappings or fake SQL syntax for unknown tables.
- Prefer existing REST endpoints over raw SQL where they already expose the required data.
- Keep mutation guidance behind explicit review and approval.

## Suggested Validation Tasks

- extraction prerequisite walkthrough
- identify tables and keys for ownership by `LSE_ID`
- explain `PHD_*` versus `MOD_*`
- identify forecast-related source rows for one `PRODUCTCODE`
- explain conversion-ready inputs for ARIES preparation
