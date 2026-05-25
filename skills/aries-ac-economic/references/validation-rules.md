# AC_ECONOMIC Validation Rules

## Current Baseline

The initial validator only checks generic file hygiene. Field-level validation should be added after the line format is curated.

## Planned Checks

- Required field count.
- Field type validation.
- Date parsing.
- Numeric precision and sign conventions.
- Allowed code values.
- Duplicate or conflicting line detection.
- Round-trip parse and render checks.

## Mutation Review Gate

Before writing `AC_ECONOMIC` changes, produce:

- Source identifier and row count.
- Proposed changed lines.
- Validation output.
- Assumptions.
- Backup or rollback plan.
- Explicit user approval requirement.
