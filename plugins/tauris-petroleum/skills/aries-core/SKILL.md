---
name: aries-core
description: Use for ARIES application workflows, shared ARIES terminology, table navigation, export/import handling, and cross-table petroleum economics context. Use this before narrower ARIES skills when the task spans multiple ARIES modules or the right ARIES skill is unclear.
---

# ARIES Core

Use this skill for shared ARIES context and for routing work to narrower ARIES skills.

## Workflow

1. Identify the ARIES area involved: economics, reserves, ownership, forecasts, pricing, scenarios, imports, or exports.
2. Load the narrow skill when one exists. Use `aries-ac-economic` for `AC_ECONOMIC` table lines.
3. Confirm whether the task is read-only, draft-only, or mutating.
4. For mutating workflows, produce a dry-run artifact and ask for review before writing anything.
5. Keep unverified ARIES behavior out of scripts and generated mutation steps.

## References

- `references/module-map.md`: curated ARIES areas and planned skill split.
