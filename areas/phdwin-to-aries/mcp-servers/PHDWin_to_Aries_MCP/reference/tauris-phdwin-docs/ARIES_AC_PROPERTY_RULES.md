# AC_PROPERTY Rules

This file defines the hard and fast export rules for `AC_PROPERTY`.

Use this as the first strict Aries export contract while the broader template-driven schema work continues.

## Priority

`AC_PROPERTY` is the highest-priority Aries export table for structural correctness.

If there is a conflict between:

- dynamic export generation
- inferred dictionary keys
- C# property names
- temporary normalization logic

and the rules below, the rules below win.

## Table Name

- table name must be `AC_PROPERTY`

## Column Naming Rules

For `AC_PROPERTY`, all final Access column names must be:

- uppercase
- no spaces
- no special characters
- underscores only where needed

Examples:

- `DBSKEY`
- `PROPNUM`
- `PRIOR_OIL`
- `PRIOR_GAS`
- `PRIOR_WTR`

Do not allow:

- lowercase column names
- mixed-case drift from source dictionaries
- ad hoc spacing
- punctuation-driven names

## Key

`AC_PROPERTY` key:

- `DBSKEY`
- `PROPNUM`

These are keyed items and must always be present in the final export.

## Required Structural Intent

At minimum, the export writer should treat these columns as core structural fields:

- `DBSKEY`
- `PROPNUM`
- `SEQ`
- `MAJOR`
- `PRIOR_OIL`
- `PRIOR_GAS`
- `PRIOR_WTR`

This list can grow as the template contract is refined, but these should not drift.

## Writer Behavior

The Aries Access writer should eventually handle `AC_PROPERTY` like this:

1. Start from the Aries template guidance.
2. Apply Taurus `AC_PROPERTY` rules from this file.
3. Build the final column list explicitly.
4. Map source values into those exact uppercase target columns.
5. Validate `DBSKEY + PROPNUM` uniqueness before insert where practical.
6. Avoid dynamic column creation based purely on dictionary casing.

## Anti-Pattern

These are considered incorrect for `AC_PROPERTY`:

- writing lowercase column headers
- deriving final column names directly from current dictionary keys
- allowing casing to vary by source dataset
- treating `AC_PROPERTY` as a generic dump table

## Relationship To Template

The Aries template `.accdb` is the schema guide.

However, for `AC_PROPERTY`, Taurus export rules are stricter:

- use the template as guidance
- enforce Taurus uppercase naming rules
- preserve `DBSKEY` and `PROPNUM` as the effective key pair

## Next Step

After this rule file, the next step is to create the explicit final `AC_PROPERTY` column list from the Aries template and lock the writer to that list.
