# Claude Adapter

Use this adapter when loading `phdwin-v2-querying` into Claude as a project instruction set, shared context file, or reusable prompt wrapper.

## Purpose

Claude should use the core skill to help users:

- understand PhdWIN v2 extraction prerequisites
- confirm the Clarion TopSpeed driver requirement
- interpret extracted `PHD_*` and `MOD_*` tables
- explain key fields and join logic
- draft safe read-only query paths
- turn prior ARIES-conversion lookup knowledge into standalone `SELECT` guidance

## Load Order

Start with:

1. `SKILL.md`
2. `references/workflow/extraction-guide.md`
3. `references/schema/schema-notes.md`
4. `references/lookups/select-query-map.md`

Load these as needed:

- `references/workflow/api-endpoints.md`
- `references/workflow/query-patterns.md`
- `references/schema/generated-entity-map.md`
- `references/source-library/reference-inputs-index.md`

## Claude Instructions

- Treat `SKILL.md` as the primary workflow.
- Prefer verified repo evidence before inference.
- If a conclusion comes mainly from the `reference-inputs` document library, say so explicitly.
- Distinguish clearly between:
  - extraction prerequisites
  - extracted-table interpretation
  - query drafting
  - reusable read-only lookup logic
- If the user lacks the Clarion TopSpeed ODBC driver, tell them they need it and should contact Tauris AI or SoftVelocity.
- Ask about the driver only when the source is native `.phz`, `.phd`, or `.mod`.
- If the source is already SQLite, skip the driver prerequisite and move to schema/table checks.
- Do not invent undocumented table meanings or joins.

## Suggested Project Instruction

```text
Use the PhdWIN v2 querying skill as the source of truth for extraction prerequisites, Clarion driver guidance, extracted SQLite table layout, key logic, and safe read-only query drafting. Reuse prior conversion knowledge only as a source for lookup logic, not export logic. Prefer repo-verified schema notes and generated entity mappings before making assumptions. When the answer depends mainly on the external reference library, say so explicitly.
```

## Suggested Test Prompts

```text
I have a PhdWIN v2 dataset but no Clarion TopSpeed driver. What do I need before extraction?
```

```text
Which extracted tables hold case identity, ownership, forecast inputs, and production history, and what keys join them?
```

```text
For one LSE_ID, what tables should I query to find the initial oil decline rate?
```
