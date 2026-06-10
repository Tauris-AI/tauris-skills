# Aries Access Writer

`aries_access_writer.py` is the shared Access write path for this repo.

Use it when a workflow already has normalized ARIES table payloads and needs to
populate a template-backed `.accdb`.

Current caller:

- PHDWin v2 conversion review export

Intended callers:

- auto-forecasting ARIES payload export
- generated-from-scratch ARIES database builds
- future AI workflow payload builders

## Contract

Callers provide a dictionary of table rows:

```python
tables = {
    "AC_PROPERTY": [{...}],
    "AC_PRODUCT": [{...}],
    "AC_ECONOMIC": [{...}],
    "AC_SCENARIO": [{...}],
    "PROJECT": [{...}],
    "PROJLIST": [{...}],
}
```

The writer handles:

- copying the supplied Access template
- connecting through the Access ODBC driver with required metadata decoders
- matching real target columns from `SELECT * FROM [table] WHERE 1=0`
- optional governed column additions
- empty-string to `NULL` coercion
- scoped deletes before insert
- insert ordering
- post-write orphan checks
- per-table write summaries

The writer does not invent conversion logic. PHDWin conversion, auto-forecasting,
and other workflows must build their own ARIES table payloads before calling the
writer.
