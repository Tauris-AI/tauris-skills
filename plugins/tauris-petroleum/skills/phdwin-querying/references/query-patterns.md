# PhdWIN Query Patterns

## Defaults

- Use read-only queries unless mutation is explicitly requested and approved.
- Parameterize user-provided values.
- Select only the columns needed for the business question.
- Include row limits while exploring unfamiliar schemas.
- Avoid credentials and raw connection strings in prompts, scripts, or committed files.

## Query Review Checklist

- Business question is stated.
- Tables or views are named.
- Joins are justified.
- Filters are explicit.
- Units and date ranges are clear.
- Assumptions are listed.
