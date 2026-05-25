---
name: aries-ac-economic
description: Use for reading, validating, drafting, or writing ARIES AC_ECONOMIC table lines, including line parsing, field-level review, synthetic examples, dry-run mutation plans, and deterministic validation scripts.
---

# ARIES AC_ECONOMIC

Use this skill when a task involves ARIES `AC_ECONOMIC` table lines.

## Workflow

1. Determine whether the request is read-only, draft-only, or write-intended.
2. Load `references/line-format.md` for the current documented line format.
3. Load `references/validation-rules.md` before validating, generating, or modifying lines.
4. Use `scripts/validate_ac_economic.py` for repeatable checks when examples or proposed output are present.
5. For write-intended work, produce a dry-run summary first: source rows, proposed changed rows, assumptions, and rollback or restore plan.

## Guardrails

- Do not invent field meanings. Mark unknown fields as unverified.
- Do not include raw production exports in skill references.
- Do not write directly to ARIES without an explicit user approval after review.
- Prefer synthetic examples until real examples have been scrubbed.

## References

- `references/line-format.md`: curated field and line-format notes.
- `references/validation-rules.md`: deterministic checks and review gates.
