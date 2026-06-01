# AC_ECONOMIC Validation Rules

## Current Baseline

The canonical validator is the `tauris-aries` CLI. It validates the structured JSON document emitted by `tauris-aries decode` and rejects edits that would silently drop unsupported raw source rows.

```bash
tauris-aries validate econ.json
tauris-aries roundtrip --sqlite ARIESGeneric.sqlite
```

The older `scripts/validate_ac_economic.py` helper is only a legacy hygiene check and should not be treated as the canonical parser.

## Implemented Checks

- Required document format.
- Required row metadata such as property number, section, sequence, keyword, and expression.
- Allowed `AC_ECONOMIC` section numbers.
- Duplicate row sequence detection per property, section, and qualifier.
- Unsupported row passthrough protection.
- Round-trip row count and normalized row comparison.

## Planned Checks

- Date parsing.
- Numeric precision and sign conventions.
- Allowed code values.
- Section-specific unit validation.
- Unknown stream lookup validation when lookup tables are available.
- Broader semantic parity against the Tauris importer.

## Mutation Review Gate

Before writing `AC_ECONOMIC` changes, produce:

- Source identifier and row count.
- Proposed changed lines.
- Validation output.
- Assumptions.
- Backup or rollback plan.
- Explicit user approval requirement.
