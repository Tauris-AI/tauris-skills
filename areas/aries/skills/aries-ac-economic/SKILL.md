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
4. Prefer the `tauris-aries` CLI for repeatable checks when SQLite exports or proposed JSON edits are present.
5. Use this safe edit loop: decode SQLite to structured JSON, edit JSON, validate JSON, encode to a row export, then review the diff/output.
6. For write-intended work, produce a dry-run summary first: source rows, proposed changed rows, assumptions, and rollback or restore plan.

## Deterministic CLI

Use the canonical .NET CLI from `tauris-aries` when available:

```bash
tauris-aries decode --sqlite ARIESGeneric.sqlite --out econ.json
tauris-aries validate econ.json
tauris-aries encode econ.json --out AC_ECONOMIC.csv
tauris-aries roundtrip --sqlite ARIESGeneric.sqlite
tauris-aries inspect-unsupported --sqlite ARIESGeneric.sqlite --out unsupported.json
tauris-aries export-schema --out aries-econ.schema.json
```

If the binary is not installed on `PATH`, use the local publish output or run through `dotnet` inside the `tauris-aries` devcontainer.

## Guardrails

- Do not invent field meanings. Mark unknown fields as unverified.
- Do not freehand-write raw ARIES syntax when a decode/validate/encode path is available.
- Unsupported rows must be preserved unless a human explicitly approves editing the raw text.
- Do not include raw production exports in skill references.
- Do not write directly to ARIES without an explicit user approval after review.
- Prefer synthetic examples until real examples have been scrubbed.

## References

- `references/line-format.md`: curated field and line-format notes.
- `references/validation-rules.md`: deterministic checks and review gates.
