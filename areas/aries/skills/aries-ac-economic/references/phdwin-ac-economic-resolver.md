# PHDWin AC_ECONOMIC Resolver

This reference captures the current Tauris PHDWin-to-ARIES `AC_ECONOMIC` parsing and review-row behavior. Use it when the task involves the Python Cowork exporter, PHDWin source tables, conversion diagnostics, or explaining why generated `AC_ECONOMIC` rows are not yet final ARIES economic syntax.

For production-grade AC_ECONOMIC taxonomy and line-generation best practice, read `aries-ac-economic-best-practices.md` first. The Python review-row scaffold should move toward that Tauris conversion behavior, not redefine it.

## Current Boundary

The current Python path is a deterministic diagnostics scaffold, not final ARIES economic parity.

- Runtime module: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/scripts/aries_economic.py`
- Export caller: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/scripts/aries_export.py`
- Tests: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/scripts/test_aries_economic.py`
- Design plan: `areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/aries-conv-docs/AC_ECONOMIC_DEEP_FIDELITY_PLAN.md`

Generated rows are coverage artifacts with `QUALIFIER = PY_REVIEW` and `KEYWORD` values such as `PY_REVIEW_FORECAST`. They preserve source facts for review and reconciliation. Do not present them as verified final ARIES line syntax.

## Source Tables

Required:

- `PHD_FORCAST`

Recommended:

- `PHD_PRODUCTNAMES`
- `PHD_LSESEGMENT`
- `PHD_LSEPRODVAL`
- `PHD_ECON`
- `PHD_INVEST`
- `PHD_INVESTDESCR`
- `PHD_CUMVOL`
- `MOD_SCEN`
- `MOD_TEMPLATE`

Missing required tables block deep-fidelity generation. Missing recommended tables should produce warnings and diagnostics, not silent success.

## Target Row Shape

The effective `AC_ECONOMIC` key is:

- `PROPNUM`
- `SECTION`
- `SEQUENCE`

Current review rows include:

- `PROPNUM`: generated as `PHD{LSE_ID:06d}`
- `SECTION`: source-surface section number
- `SEQUENCE`: deterministic order within the source surface
- `QUALIFIER`: `PY_REVIEW`
- `KEYWORD`: source-review keyword
- `EXPRESSION`: semicolon-delimited source field/value facts
- `LINE`: keyword plus expression
- `SOURCE_TABLE`
- `SOURCE_LSE_ID`
- source-specific trace fields such as `SOURCE_ARCSEQ`, `SOURCE_PRODUCTCODE`, `SOURCE_PRODUCT_NAME`, `SOURCE_INVESTDESCR_ID`, and `SOURCE_INVEST_DESCRIPTION`

Rows without usable `LSE_ID` are skipped and counted in diagnostics.

## Current Section Map

| Section | Source table | Keyword |
|---:|---|---|
| 1 | `PHD_FORCAST` | `PY_REVIEW_FORECAST` |
| 2 | `PHD_ECON` | `PY_REVIEW_ECON` |
| 3 | `PHD_INVEST` | `PY_REVIEW_INVEST` |
| 4 | `PHD_LSESEGMENT` | `PY_REVIEW_SEGMENT` |
| 5 | `PHD_LSEPRODVAL` | `PY_REVIEW_PRODVAL` |
| 6 | `MOD_SCEN` | `PY_REVIEW_SCEN` |
| 7 | `MOD_TEMPLATE` | `PY_REVIEW_TEMPLATE` |
| 8 | `PHD_CUMVOL` | `PY_REVIEW_CUMVOL` |

Sequence numbers are independent by generated source section in tests. Forecast rows sort by `LSE_ID`, `ARCSEQ`/sequence, product code, and start date. Generic rows sort by `LSE_ID`, `SEQ`, investment/econ identifier, and date/start date.

## Field Preservation

The resolver builds `EXPRESSION` from known candidate fields first. If none are present, it falls back to all source columns sorted by column name.

Forecast candidates include lease id, arc/sequence, product code, start date, `Q`, `QI`, rate, decline, b/exponent, minimum decline, and limit/economic-limit fields.

Econ candidates include lease id, sequence/case ids, start date, price fields, differentials, severance/ad valorem tax, operating cost, fixed/variable cost, LOE, and escalation.

Investment candidates include lease id, sequence/investment ids, description id, date, amount/cost/capital, tangible/intangible, and abandonment.

Segment/product-value/cumulative-volume candidates preserve product, rate/decline, price/differential, shrink/yield/BTU, dates, and cumulative volumes when present.

## Product And Investment Lookups

`PHD_PRODUCTNAMES` is indexed by product code. When a product code matches, the resolver appends `PRODUCT_NAME=...` and fills `SOURCE_PRODUCT_NAME`.

Unmatched product codes are counted by source table for:

- `PHD_FORCAST`
- `PHD_LSESEGMENT`
- `PHD_LSEPRODVAL`
- `PHD_CUMVOL`

`PHD_INVESTDESCR` is indexed by description/investment identifier. When a `PHD_INVEST` row matches, the resolver appends `INVEST_DESCRIPTION=...` and fills `SOURCE_INVEST_DESCRIPTION`. Unmatched investment description ids are counted and warned.

## Diagnostics To Surface

Report these diagnostics in summaries when present:

- `tableCounts`
- `scopedTableCounts`
- `missingLeaseIdCounts`
- `unmatchedProductCodeCounts`
- `productNameCount`
- `missingRequiredTables`
- `missingRecommendedTables`
- `selectedLeaseIds`
- per-section review row counts
- `reviewRowCount`
- `unmatchedInvestDescriptionCount`
- `status`: `source_review_rows` or `diagnostics_only`

Always surface the warning that current Python rows are review rows only when rows are generated.

## Known Gap

Final ARIES economics still require curation/reconciliation of:

- true ARIES economic keywords and expressions
- section names and final section ordering
- setup/common/default line merge behavior
- scenario and template behavior
- sidefile, lookup, macro, and setup dependencies
- product stream handling and unit conventions
- price/differential/cost/capital timing and signs
- known-good output comparison against `ARIES_UG001.chm`, vendor docs, and reviewed examples

Use this resolver knowledge to explain, test, and improve the conversion scaffold. Do not use it as authority for final ARIES syntax without verified examples or vendor-documentation support.
