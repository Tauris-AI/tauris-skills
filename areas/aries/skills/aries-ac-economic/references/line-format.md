# AC_ECONOMIC Line Format

This reference supports documentation-first drafting of proposed ARIES `AC_ECONOMIC` lines. For usable grammar, read `ac-economic-line-grammar.md` and `ac-economic-keyword-catalog.md`; this file is the short row-shape overview.

## Drafting Boundary

Agents may draft new lines from this reference without opening a database. Drafts must be labeled as proposed dry-run output and must separate:

- verified behavior
- inferred behavior
- unknown behavior requiring SME or example confirmation

Use database inspection only when the user supplies an ARIES `.accdb`, `.mdb`, SQLite export, or existing row set and asks for validation against it.

## Structured Row Shape

Represent proposed rows with this minimum structure:

| Field | Purpose |
|---|---|
| `propnum` | ARIES property/case identifier. |
| `section` | `AC_ECONOMIC` section number. |
| `sequence` | Row order within property, section, and qualifier context. |
| `qualifier` | Optional qualifier or phase/context when known. |
| `keyword` | ARIES economic line keyword or mnemonic. |
| `expression` | Remaining line expression/arguments exactly as proposed. |
| `basis` | `verified`, `inferred`, or `unknown`. |
| `notes` | Assumptions, source documentation, or validation caveat. |

## Current Tool Boundary

Use `tauris-aries` for concrete validation when source rows are available. The tool reads structured SQLite rows from `raw_AC_ECONOMIC` and exports a JSON document with:

- row metadata: `propnum`, `section`, `sequence`, `qualifier`
- row text: `keyword`, `expression`
- raw preservation: `raw.keyword`, `raw.expression`
- additive parse details under `parse`
- diagnostics under `diagnostics`

Unsupported rows remain valid document rows and must encode back from their preserved raw values.

## Related References

- `ac-economic-line-grammar.md`: fixed row and expression forms.
- `ac-economic-calculations.md`: decline and ratio calculations used before writing expressions.
- `ac-economic-keyword-catalog.md`: curated keyword and section catalog.

## Remaining Curation Inputs

- Sanitized sample lines.
- Field list and field order.
- Required versus optional fields.
- Allowed codes and enum values.
- Numeric precision and rounding expectations.
- Date format expectations.
- Known application-side defaults.

## Documentation Rule

For each field, record whether the behavior is verified, inferred, or unknown. Deterministic scripts should enforce only verified rules.
