# Curation Principles

Skills in this repository should be narrow, testable, and honest about what is known.

## Write Skills Around Workflows

Prefer one skill per repeatable workflow or domain surface. ARIES should become a family of skills, not one large file. For example, `aries-ac-economic` can focus on one table and line format while `aries-core` carries shared concepts.

## Separate Procedure From Reference

Keep `SKILL.md` short. Put schemas, field notes, examples, and longer domain explanations in `references/` files so agents load them only when needed.

## Avoid Invented Rules

If a schema detail, field meaning, or application behavior has not been verified, mark it as unverified and keep it out of deterministic scripts. Use synthetic examples until real examples are sanitized.

## Prefer Deterministic Validation

For fragile formats such as ARIES table lines, add scripts that validate shape and invariants. The agent should use scripts for repeatable checks instead of relying only on prose.

## Require Review Before Mutation

Any skill that writes database rows, ARIES tables, economics inputs, forecasts, price decks, ownership, or reserves data must include a dry-run or review gate before mutation.
