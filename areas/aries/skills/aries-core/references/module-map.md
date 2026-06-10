# ARIES Module Map

This file is the starting inventory for ARIES skill curation.

## Planned Skill Areas

- ARIES core navigation and shared terminology.
- ARIES `AC_ECONOMIC` table line parsing and writing.
- ARIES economics inputs and scenario review.
- ARIES reserves and forecast review.
- ARIES price deck and differential handling.
- ARIES ownership and interest validation.
- ARIES imports, exports, and database-safe mutation workflows.
- Shared ARIES Access payload and writer contract.

## Curation Notes

Keep verified behavior separate from assumptions. When adding table-specific guidance, include the source of the knowledge, sanitized examples, and validation rules.

## Shared Writer

The shared Access writer lives at:

`areas/aries/mcp-servers/aries-mcp/aries_access_writer.py`

Source-specific builders should generate normalized ARIES table payloads and call
that writer. They should not duplicate Access ODBC connection, column matching,
delete, insert, or referential-integrity logic.

Related references:

- `aries-access-payload-contract.md`
- `aries-access-write-checklist.md`
