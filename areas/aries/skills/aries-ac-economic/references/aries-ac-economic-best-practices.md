# ARIES AC_ECONOMIC Best Practices

This reference is the preferred operating guide for `AC_ECONOMIC` taxonomy and line generation in Tauris workflows. It is grounded in:

- Tauris.PhdWin conversion methods that generate and resolve ARIES economic lines.
- The extracted `ARIES_UG001.chm` economics, MultiGraph, scenario, appendix, and import/export help pages.
- Existing Tauris `tauris-skills` conversion notes and table contracts.

Use Tauris conversion behavior as best practice when it is more specific than the vendor manual. Use the vendor manual to verify ARIES concepts, legal units, section meanings, qualifier behavior, and economics-table intent.

## Core Row Contract

`AC_ECONOMIC` rows are line records, not generic facts. Expression field count is not universal; parse by `SECTION + KEYWORD`. Treat this row shape as the contract:

| Column | Rule |
|---|---|
| `PROPNUM` | ARIES property/case id. Use the conversion's property-number convention for generated rows. |
| `SECTION` | Numeric ARIES economic section. The section controls parsing rules and run-time meaning. |
| `SEQUENCE` | Ordered line number within a property and section after all generated, sidefile, lookup, and diagnostic lines are assembled. |
| `QUALIFIER` | Scenario selector. Blank/unqualified lines are always active. Qualified lines are selected by scenario section rules. |
| `KEYWORD` | ARIES economic keyword, phase keyword, ditto keyword `"`, `TEXT`, `SIDEFILE`, `LOAD`, `LOOKUP`, `START`, `ENDDATE`, etc. |
| `EXPRESSION` | Remaining ARIES expression exactly as ARIES should interpret it. Preserve units, timing units, stream references, and macros. |

Always sort final rows by `SECTION`, then `SEQUENCE`. Resequence each section to a contiguous sequence after expansion or edits.

## Section Taxonomy

Tauris and the ARIES manual align on these practical sections:

| Section | Meaning | Common Tauris examples |
|---:|---|---|
| 1 | Miscellaneous/title/setup-style lines | `TITLES`; cost-case marker |
| 2 | Production/input settings level controls | `WELLS`, `BTU`, `ELOSS`, `LIFE` |
| 4 | Production/forecast/economic production lines | `START`, `*START`, product phase keywords, `LOAD`, formula lines, `ENDDATE` |
| 5 | Prices | price/differential/adustment lines such as `PAJ/<phase>` and `PAD/<phase>` |
| 6 | Expenses/taxes/costs | operating cost, severance/ad valorem/tax style lines |
| 7 | Ownership | `NET`, ditto keyword `"`, reversion triggers and interests |
| 8 | Investments/capital | investment template lines and partner-qualified capital |
| 9 | Overlay | stream arithmetic, formula overlays, volumetric shrink or derived stream adjustments |

Do not assume every database uses every section. When resolving an existing table, use the scenario table's `DATA_SECT` values and the stored rows rather than hard-coding only the common sections.

## Qualifiers And Scenarios

The ARIES manual describes qualifiers as the way ARIES distinguishes multiple sensitivities or alternatives inside economic sections. Scenarios are combinations of section-level qualifiers.

Best practice:

- Blank/null qualifier lines are always included for the section.
- Qualified lines are included only when selected by the scenario for that section.
- A scenario may provide a hierarchy of qualifiers for a section. Use the first qualifier in the hierarchy that has rows for the property/section.
- Do not calculate multiple qualifiers from the same section just because several are listed.
- If no selected qualifier has rows, include blank/unqualified rows and follow ARIES default behavior only when a verified default exists.
- Treat production section qualifier behavior carefully because forecasts saved from MultiGraph use qualifiers to distinguish multiple saved forecasts.

Tauris retrieval behavior:

1. Load scenario sections.
2. Skip section 1 in scenario-driven retrieval.
3. For each data section, test qualifier candidates in order.
4. Add rows for the first matching qualifier.
5. Add null/unqualified rows for the same section.
6. Sort by section and sequence.

## Sidefiles, Lookups, And Macros

Tauris best practice is to resolve economic rows before final interpretation:

- If a row keyword contains `FILE`, treat the expression as a sidefile reference and load sidefile rows for the same section.
- If a row keyword contains `LOOKUP`, resolve lookup expressions and expand them into concrete economic lines.
- Substitute property/database macros in expressions before parsing or evaluating.
- Apply macro substitution again to lookup-expanded expressions because lookup rows may introduce macros.
- Preserve the source qualifier through sidefile and lookup expansion.
- If macro substitution fails, do not silently drop the row. Add a `TEXT` diagnostic line and comment out the unresolved source line by prefixing the keyword with `*`.
- After expansion, resequence rows by section.

This is a best-practice preservation rule: unresolved behavior should remain visible in the economics table rather than disappearing.

## Forecast Lines

ARIES MultiGraph saves forecasts to the Economic Table and uses qualifiers to distinguish saved forecasts. Tauris conversion follows these principles:

- Generate production forecast rows in section 4.
- Use `START` lines to set the effective forecast start date.
- For recompletion cases, preserve parent timing using `*START` plus a `START ... DELAY ...` line.
- Use the product's ARIES phase keyword for the first line of a product or ratio forecast, then use the ditto keyword `"` for continuation segment lines.
- Skip zero non-major forecast segments unless a minimal cost-case line is required.
- For array/monthly loaded forecasts with future volumes, generate a `LOAD` line instead of an Arps equation.
- Add `ENDDATE` in section 4 to anchor the generated run end-date behavior.
- For cost cases, create a `TITLES` cost-case marker and a tiny nonzero production line so ARIES can run the economics path without a normal forecast.

Tauris unit handling:

- Convert `scf` to `Mcf` with a `0.001` multiplier.
- Convert gallons to barrels using `1/42` and add a `TEXT` note line documenting the conversion.
- For ratios, derive denominator units from the denominator product/unit; preserve `MM` when denominator units start with `MM`.
- Clamp generated forecast rates to a small positive value where ARIES cannot accept zero in a required forecast expression.

Formula behavior:

- Parse PHDWin product formulas into ARIES stream/phase expressions when possible.
- Use the target product phase keyword for generated formula expression lines.
- If formula parsing fails because a phase is unknown, report/log it rather than inventing a line.
- Product multipliers and shrink adjustments are represented as section 4 formula/overlay-style rows.

## Prices, Adjustments, And Segmented Values

Tauris project-variable conversion uses segment rows to build scheduled ARIES expressions:

- Add a zero/bootstrap line at the start date for the relevant price/cost/product variable.
- Add continuation rows with `"` for each positive segment value.
- Use `IMO` for incremental months and `TO LIFE` for open-ended final segments.
- Use `PC 0` for flat price/cost escalation where the source does not define an escalation.
- For PHDWin shrink, ARIES expects residual shrink, so generate `1 - shrinkPercent`.
- For volumetric shrink requiring overlay treatment, use section 9 stream arithmetic rather than a simple variable line.
- Price adjustments can become `PAJ/<phase>` lines.
- Price deductions/differentials can become `PAD/<phase>` lines.
- Convert gallon-based differentials to barrel units where applicable.

## Ownership Lines

Ownership belongs in section 7. Tauris best practice:

- Generate `NET` for the first ownership line in a group/qualifier.
- Use the ditto keyword `"` for continuation ownership/reversion lines.
- Expression values are percentages for working interest, oil revenue interest, gas revenue interest, and optional NPI.
- Use the group qualifier for ownership lines.
- Reversion conditions are appended to the previous/current ownership expression rather than treated as unrelated rows.
- Preserve supported reversion triggers such as net revenue, elapsed years, specified date, payout, cumulative oil, cumulative gas, and investment-linked payout/net revenue.
- For date-based reversions, use `MM/yyyy AD`.
- Multiplicative working-interest date switches should calculate the new working interest from the previous working interest context.

If a reversion type is not supported by the current conversion, preserve the row as review risk; do not drop it.

## Investments And Capital

Investment lines are generated from capital/investment templates:

- Use expression templates rather than handwritten one-off syntax when a recognized investment type exists.
- Substitute schedule, tangible, intangible, gross/net, and partner parameters deterministically.
- Use partner-qualified capital lines when the investment belongs to a partner context.
- Use `TAURIS` qualifier for generated abandonment and other generated global lines.
- If abandonment appears in a cost case, add a section 2 `LIFE` line at the abandonment hard date.
- Schedule hard dates as `MM/yyyy AD`; offset-based schedules may be expressed in months.

## Current Python MCP Review Rows

The Python MCP exporter in `tauris-skills` currently creates `PY_REVIEW_*` rows for coverage and diagnostics. Those rows are useful for source inventory but are not final ARIES syntax.

When improving the Python MCP exporter, migrate it toward the best-practice behavior above:

- real section taxonomy
- scenario/qualifier handling
- sidefile/lookup/macro preservation
- section resequencing
- forecast/load/formula/ownership/capital generation
- explicit warnings for unsupported behavior

Until parity is implemented, summaries must say that Python rows are review artifacts, not final ARIES economic lines.

## CHM-Derived Reference Points

The extracted ARIES user guide reinforces these concepts:

- Economic data is edited and stored in the Economic Table.
- Forecasts from MultiGraph can be saved to and retrieved from the Economic Table.
- Qualifiers distinguish alternative saved forecasts and sensitivities.
- Scenarios combine section-level qualifiers; unqualified lines remain active.
- Production, price, expense, tax, ownership, investment, overlay, and miscellaneous sections have distinct legal units and expression rules.
- Appendices list permissible production units, forecast/reversion units, price/cost/tax/interest/investment units, and escalation units.
- Import/export of economic data is line-oriented; preserve line order and section context.

Do not copy vendor manual text into public skill files. Summarize behavior and cite `ARIES_UG001.chm` as a local reference when exact wording or table contents are needed.
