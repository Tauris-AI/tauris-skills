# Aries Access Payload Contract

This contract keeps Access writing separate from source-specific conversion.

## Roles

Source builders create ARIES table payloads:

- PHDWin v2 builder: PHDWin SQLite source tables to ARIES rows
- auto-forecasting builder: production/forecast outputs to ARIES rows
- manual/AI workflow builder: approved assumptions to ARIES rows

The shared Access writer writes those payloads into a template-backed `.accdb`.

## Payload Shape

```python
tables: dict[str, list[dict[str, object]]]
```

Keys are ARIES table names, for example:

- `AC_PROPERTY`
- `AC_PRODUCT`
- `AC_TEST`
- `AC_DAILY`
- `AC_ECONOMIC`
- `AC_OWNER`
- `AC_SCENARIO`
- `AC_SETUPDATA`
- `PROJECT`
- `PROJLIST`
- `SORTFILTERS`
- `SelFilters`

Rows should use ARIES-facing column names. The writer can apply small governed
column aliases, but it should not perform source-specific interpretation.

## Completion Rules

For inspectable databases, it is acceptable for some ARIES tables to be empty by
design when source evidence is missing.

For runnable economic databases:

- `AC_PROPERTY` must contain the selected property rows.
- `PROJECT` and `PROJLIST` must select only real generated properties.
- `AC_PRODUCT` must contain monthly/historical production when available.
- `AC_ECONOMIC` must contain final ARIES economic rows, not `PY_REVIEW` rows.
- Every `AC_ECONOMIC.PROPNUM` must exist in `AC_PROPERTY.PROPNUM`.
- Every generated economic qualifier must be selectable by `AC_SCENARIO`.

`PY_REVIEW` rows are diagnostics only. They prove source coverage; they do not
make an economic export complete.
