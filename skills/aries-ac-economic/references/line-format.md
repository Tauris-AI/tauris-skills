# AC_ECONOMIC Line Format

This reference is intentionally sparse until the ARIES line format is curated from verified examples.

## Current Tool Boundary

Use `tauris-aries` for concrete `AC_ECONOMIC` handling. The tool reads structured SQLite rows from `raw_AC_ECONOMIC` and exports a JSON document with:

- row metadata: `propnum`, `section`, `sequence`, `qualifier`
- row text: `keyword`, `expression`
- raw preservation: `raw.keyword`, `raw.expression`
- additive parse details under `parse`
- diagnostics under `diagnostics`

Unsupported rows remain valid document rows and must encode back from their preserved raw values.

## Required Curation Inputs

- Sanitized sample lines.
- Field list and field order.
- Required versus optional fields.
- Allowed codes and enum values.
- Numeric precision and rounding expectations.
- Date format expectations.
- Known application-side defaults.

## Documentation Rule

For each field, record whether the behavior is verified, inferred, or unknown. Deterministic scripts should enforce only verified rules.
