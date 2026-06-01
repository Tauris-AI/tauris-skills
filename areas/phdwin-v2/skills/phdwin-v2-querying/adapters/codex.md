# Codex Adapter

Use this adapter when exposing `phdwin-v2-querying` to Codex or Codex-compatible skill loaders.

## Purpose

Codex should use the core skill to:

- walk users through PhdWIN v2 extraction prerequisites
- confirm Clarion TopSpeed driver requirements
- explain the extracted SQLite table layout used by the local workflow
- map business questions onto `PHD_*` and `MOD_*` tables
- explain keys and join logic
- draft safe read-only query paths
- support standalone read-only lookup logic derived from prior conversion work

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
- lookup design:
  - `references/lookups/select-query-map.md`

## Codex Instructions

- Use the skill progressively. Do not load every reference file unless the task needs it.
- Anchor table names and routes in the checked-in generated entities and server code first.
- Explicitly separate verified facts from inferred guidance.
- Do not rely on proprietary vendor help files or local-only reference-input folders.
- When the user is pre-extraction, prioritize driver/setup guidance over query examples.
- When the user already has extracted tables, prioritize table purpose, keys, joins, and read-safe access paths.
- When the task references older conversion work, reuse only the table/key lookup logic and keep the result read-only.
- Prefer scriptable low-level steps over an interactive wizard until the underlying runner is proven.

## Behavioral Rules

- If the Clarion TopSpeed ODBC driver is missing, state that direct extraction requires it and that the user must install it before native extraction can proceed.
- Apply that driver requirement only to native `.phz`, `.phd`, or `.mod` sources.
- If the source is already SQLite, move directly to database-open, table, and key checks.
- Do not invent unsupported mappings or fake SQL syntax for unknown tables.
- Prefer existing REST endpoints over raw SQL where they already expose the required data.
- Keep mutation guidance behind explicit review and approval.

## Suggested Validation Tasks

- extraction prerequisite walkthrough
- identify tables and keys for ownership by `LSE_ID`
- explain `PHD_*` versus `MOD_*`
- identify forecast-related source rows for one `PRODUCTCODE`
- explain read-only lookup paths for common well and project questions
