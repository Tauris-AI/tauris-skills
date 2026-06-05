---
name: aries-ac-economic
description: Use for reading, validating, drafting, or writing ARIES AC_ECONOMIC table lines, including line parsing, field-level review, synthetic examples, dry-run mutation plans, and deterministic validation scripts.
---

# ARIES AC_ECONOMIC

Use this skill when a task involves ARIES `AC_ECONOMIC` table lines. A database is optional: use the references to draft proposed new lines from documented assumptions, and use database/CLI validation only when source rows or a review export are supplied.

## Workflow

1. Determine whether the request is read-only, draft-only, or write-intended.
2. Load `references/line-format.md` for the current documented line format.
3. Load `references/validation-rules.md` before validating, generating, or modifying lines.
4. For AC_ECONOMIC taxonomy, scenario/qualifier behavior, section ordering, sidefile/lookup expansion, forecast lines, ownership lines, or Tauris conversion best practice, load `references/aries-ac-economic-best-practices.md`.
5. For forecast grammar, variable-length fixed-position expressions, ratio-line form, valid units, sections, and sequence rules, load `references/ac-economic-line-grammar.md`.
6. For decline conversions, Dmin terminal-switch semantics, and ratio math, load `references/ac-economic-calculations.md`.
7. For keyword/section lookup, load `references/ac-economic-keyword-catalog.md`.
8. For PHDWin-to-ARIES Python exporter or source-table parsing work, load `references/phdwin-ac-economic-resolver.md`.
9. For draft-only work, produce proposed lines plus assumptions, unknowns, and validation notes without asking for a database.
10. Prefer the `tauris-aries` CLI for repeatable checks when SQLite exports or proposed JSON edits are present.
11. Use this safe edit loop when source rows exist: decode SQLite to structured JSON, edit JSON, validate JSON, encode to a row export, then review the diff/output.
12. For write-intended work, produce a dry-run summary first: source rows, proposed changed rows, assumptions, and rollback or restore plan.

## Drafting Without A Database

When the user wants to create new lines from assumptions or documentation:

1. Identify the target `PROPNUM`, `SECTION`, `SEQUENCE`, and optional qualifier context.
2. Select the documented keyword or line family from `references/line-format.md`.
3. Draft the proposed keyword/expression text.
4. State which parts are verified, inferred, or unknown.
5. Return the result as a dry-run artifact, not a direct database mutation.

Do not ask for an ARIES database unless the user asks to inspect existing rows, validate against supplied rows, or write into a live/export database.

## Deterministic CLI

Use the canonical .NET CLI from `tauris-aries` when available and when a SQLite export or structured edit document exists:

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
- `references/aries-ac-economic-best-practices.md`: Tauris conversion best practices plus ARIES_UG001-derived taxonomy for sections, qualifiers, sidefiles/lookups, forecasts, ownership, and generated line ordering.
- `references/ac-economic-line-grammar.md`: operational grammar for AC_ECONOMIC row shape, variable-length fixed-position expressions, terminal-Dmin switch rows, ratio lines, units, sections, qualifiers, and sequence rules.
- `references/ac-economic-calculations.md`: decline conversion, terminal Dmin semantics, ratio math, and export calculation rules.
- `references/ac-economic-keyword-catalog.md`: curated Tauris keyword/section catalog for phases, prices, costs, taxes, ownership, capital, overlays, and generated controls.
- `references/validation-rules.md`: deterministic checks and review gates.
- `references/phdwin-ac-economic-resolver.md`: current Tauris/PHDWin source-table parsing, Python review-row behavior, diagnostics, and known gap between review rows and final ARIES syntax.
