---
name: phdwin-querying
description: Use for querying PhdWIN databases, translating petroleum engineering questions into safe database reads, documenting schema assumptions, and drafting parameterized read-only SQL before any approved mutation workflow.
---

# PhdWIN Querying

Use this skill when a task involves PhdWIN database access, query drafting, or schema interpretation.

## Workflow

1. Restate the business question in petroleum engineering terms.
2. Identify the minimum required tables, views, or exports.
3. Default to read-only SQL.
4. Use parameters for asset, well, date, case, scenario, and owner inputs.
5. Mark schema assumptions clearly when the exact database version or customization is unknown.
6. For mutation requests, produce a dry-run plan and require explicit approval before writes.

## References

- `references/query-patterns.md`: safe query drafting patterns.
- `references/schema-notes.md`: curated schema landmarks and assumptions.
