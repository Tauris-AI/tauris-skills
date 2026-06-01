# Copilot Adapter

Use this adapter when turning `phdwin-v2-querying` into GitHub Copilot instructions, prompt files, or repo guidance.

## Purpose

Copilot should use the skill to help with:

- PhdWIN v2 extraction setup
- Clarion driver requirement explanation
- extracted table interpretation
- key and join explanation
- safe read-only query drafting
- read-only lookup tasks derived from prior conversion work

## Preferred Reference Order

1. `SKILL.md`
2. `references/schema/schema-notes.md`
3. `references/workflow/query-patterns.md`

Load these when relevant:

- `references/workflow/extraction-guide.md`
- `references/workflow/api-endpoints.md`
- `references/schema/generated-entity-map.md`
- `references/lookups/select-query-map.md`
- `references/source-library/reference-inputs-index.md`

## Copilot Guidance

- Keep answers short and operational unless the user asks for detail.
- Prefer concrete table/key references over generic petroleum-economics explanations.
- If code comments or docs are being generated, use the exact PhdWIN table names and preserve `FORCAST` spelling where applicable.
- If the user is missing prerequisites, tell them before generating query logic.
- Only treat the Clarion driver as a prerequisite for native `.phz`, `.phd`, or `.mod` inputs.
- If the user already has SQLite output, move directly to table and query guidance.
