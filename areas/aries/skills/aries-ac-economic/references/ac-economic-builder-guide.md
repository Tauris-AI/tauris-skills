# AC_ECONOMIC Builder Guide

Use this guide when asking Claude Cowork to script or review ARIES `AC_ECONOMIC`
lines for a generated ARIES Access database. It supports two related workflows:

- PHDWin-to-ARIES conversion, where Tauris.PhdWin source tables contain most of
  the economic intent.
- Non-PHDWin proforma builds, such as Enverus history-to-ARIES, where production
  history and property identity may be available but many economic sections are
  intentionally empty or defaulted.

Tauris.PhdWin is the reference implementation for ARIES row shape, section
behavior, scenario selection, sidefile/lookup handling, and safe failure modes.
Do not assume non-PHDWin source data has PHDWin economics. When behavior is
uncertain or data is absent, leave sections empty, create minimal governed
defaults, or add review notes instead of inventing final ARIES syntax.

Primary Tauris.PhdWin references:

- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.PhdWin.Server/Endpoints/Aries/AriesExportService.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.PhdWin.Server/Endpoints/Forecast/ForecastViewModelRepository.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.PhdWin.Server/Endpoints/ProjectVariable/ProjectVariableRepository.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.PhdWin.Server/Endpoints/Ownership/OwnershipRepository.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Aries.Common/Services/IAriesService.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Aries.Common/Endpoints/Econ/EconRepository.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Aries.Common/Endpoints/Scenario/ScenarioRepository.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Aries.Common/Endpoints/Sidefile/SidefileRepository.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Aries.Parser/Codegen/AriesParser.g4`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Odbc.Objects/AriesEconEntity.cs`
- `/mnt/c/Dev/Tauris.PhdWin/src/Tauris.Odbc.Objects/EconBase.cs`

## Prompt To Give Claude Cowork

```text
Use the Tauris ARIES AC_ECONOMIC builder guide and reference Tauris.PhdWin source behavior.
Build a dry-run AC_ECONOMIC plan across sections 1-9 before writing rows.
For each proposed row, include PROPNUM, SECTION, SEQUENCE, QUALIFIER, KEYWORD,
EXPRESSION, source table/field evidence, and confidence: Verified Tauris,
CHM-supported, or Needs verification. Preserve unsupported or unclear source
behavior as TEXT/comment review rows rather than dropping it.
```

## Core Row Contract

`AC_ECONOMIC` is line-oriented. Do not model it as a generic key/value table.

Required row shape:

| Column | Builder rule |
|---|---|
| `PROPNUM` | ARIES property/case id. Match `AC_PROPERTY.PROPNUM`. |
| `SECTION` | Integer section. Section controls grammar and legal keywords. |
| `SEQUENCE` | Contiguous order within `PROPNUM + SECTION` after all generated rows, sidefiles, lookups, diagnostics, and comments are assembled. |
| `QUALIFIER` | Blank means always active. Nonblank is scenario-selected. |
| `KEYWORD` | ARIES keyword, ditto keyword `"`, `TEXT`, `SIDEFILE`, `LOOKUP`, `LOAD`, `START`, `ENDDATE`, etc. |
| `EXPRESSION` | Exact ARIES expression body for the keyword and section. Do not assume one universal token count. |

Tauris.PhdWin sequencing behavior:

- `EconBase.GetNextSequence(section)` appends within a section.
- `IAriesService.ResequenceEconTable()` resequences sections 1-9 after expansion.
- Final order is `SECTION`, then `SEQUENCE`.

## Builder Pass Order

For PHDWin conversion, follow the same practical order Tauris.PhdWin uses in
`AriesExportService.GetLeaseEconTableAsync`:

1. Forecast rows from forecast/model data.
2. Project variable rows: titles, controls, prices, costs, taxes, sidefiles, investments, formulas.
3. Ownership rows.
4. Sidefile, lookup, and macro resolution.
5. Resequence by section.
6. Validate scenario coverage and qualifier selection.
7. Export only after unsupported behavior has an explicit diagnostic row or review note.

For non-PHDWin proforma builds, use a smaller governed pass:

1. Build `AC_PROPERTY`, `AC_PRODUCT`/history, project membership, and sort/filter tables first.
2. Decide whether the database should run economics or only open as a review shell.
3. If it should run, create a minimal `AC_SCENARIO` such as `ACTIVE` across sections 1-9.
4. Populate only the `AC_ECONOMIC` rows supported by source evidence.
5. Leave unsupported sections empty rather than filling fake economics.
6. Add `TEXT` review rows only when they help the user understand a deliberate omission or unsupported assumption.
7. Validate that ARIES opens the project, renders sort/filter views, and can inspect the property before adding richer economics.

An empty `AC_ECONOMIC` section is acceptable when the source does not contain
that economic concept. A fabricated cost, price deck, ownership deck, or capital
line is worse than an empty section because it creates false economics.

## What Counts As A Fully Working Case

Use these labels when reviewing a generated ARIES database:

| Status | Meaning |
|---|---|
| `Inspectable case` | The property opens in ARIES. Project membership, sort/filter views, property identity, and history tables are usable. Economics may be empty or incomplete. |
| `Runnable shell` | The case opens and has enough scenario/setup structure for ARIES to attempt an economic run, but one or more major economic assumptions are missing or intentionally defaulted. |
| `Fully working economic case` | The case opens, is scenario-selectable, and has sourced or explicitly approved assumptions for forecast, prices, costs/taxes, ownership, and capital/abandonment where applicable. |

A fully working economic case should satisfy this checklist:

- `AC_PROPERTY` has a valid `DBSKEY`, `PROPNUM`, display identifiers, project membership, and any governed provenance columns such as `SRC_DB`.
- `PROJECT`, `PROJLIST`, `SORTFILTERS`, and `SelFilters` open without ARIES UI errors.
- `AC_PRODUCT` or equivalent history rows are populated when history exists.
- `AC_SCENARIO` selects the intended data sections and qualifiers, for example `ACTIVE` with `QUAL0=TAURIS` where generated lines use `TAURIS`.
- Section 4 has a sourced forecast, approved decline fit, approved `LOAD` forecast, or an explicit decision that the case is not intended to run forecast economics.
- Section 5 has a sourced or approved price deck if economics will be run.
- Section 6 has sourced or approved operating cost, tax, and deduction assumptions if economics will be run.
- Section 7 has sourced or approved ownership interests and reversion behavior if economics will be run.
- Section 8 has sourced or approved capital and abandonment assumptions where applicable.
- Section 9 has only supported overlay/formula rows, or is empty by design.
- Sidefiles, lookups, and macros are resolved, or unresolved items are preserved with `TEXT` diagnostics and marked as not fully working.
- Rows are sorted and resequenced by `PROPNUM + SECTION`.
- ARIES can open the project, inspect the property, and run or preview economics without crashing.

For Enverus/history-only input, the expected target is often `Inspectable case`,
not `Fully working economic case`. Promote it only when missing economic
assumptions are supplied by source data or approved by a human.

## Scenario And Qualifier Rules

Tauris.PhdWin scenario retrieval in `IAriesService.GetEconTable()`:

1. Load `AC_SCENARIO` rows for `DBSKEY + SCEN_NAME`, ordered by `DATA_SECT`.
2. Skip scenario-driven retrieval for section 1.
3. For each data section, read qualifier candidates from the scenario row.
4. Use the first qualifier that has rows for the property and section.
5. Always include null/unqualified rows for that section.
6. Return rows sorted by section and sequence.

Builder implications:

- Blank qualifier rows should contain base controls that should always run.
- Generated Tauris lines commonly use `TAURIS` as a qualifier.
- Partner/group-specific ownership and capital should use the partner/group qualifier.
- If `SCEN_NAME` differs from the intended data qualifier, set `QUAL0` explicitly in `AC_SCENARIO`.
- Do not merge multiple nonblank qualifiers for one section unless a human asks for a combined sensitivity.

## Sidefile, Lookup, Macro, And Failure Handling

Tauris.PhdWin resolution behavior in `IAriesService`:

- Keywords containing `FILE` trigger sidefile expansion through `SidefileRepository`.
- Keywords containing `LOOKUP` trigger lookup expansion.
- Macro substitution runs before final interpretation.
- Lookup-expanded expressions may also need macro substitution.
- Sidefile rows preserve `PROPNUM`, `SECTION`, and source `QUALIFIER`.
- If macro substitution fails, Tauris comments out the source row by prefixing `KEYWORD` with `*` and adds a `TEXT` diagnostic line.
- Rows are resequenced after expansion.

Builder rule:

Never silently drop unresolved sidefiles, lookups, formulas, or macros. Preserve the source and add a `TEXT` row explaining the reason.

## Section-by-Section Builder Map

For sparse non-PHDWin sources, each section below has three possible states:

- `Populated`: source data supports real ARIES lines.
- `Empty by design`: source lacks that economic concept.
- `Review only`: write `TEXT` diagnostics or external notes, not final economics.

Claude Cowork should explicitly label the state of each section before scripting rows.

### Section 1: Misc / Titles

Use for property/case descriptive lines and cost-case markers.

Common Tauris rows:

- `TITLES <lease id>, <lease name>`
- `TITLES <county>, <reservoir>`
- `TITLES <operator>`
- `TITLES COST CASE`

Builder notes:

- Keep these unqualified unless there is a verified scenario-specific reason.
- Section 1 is not selected through the scenario retrieval loop in Tauris.PhdWin.
- For Enverus-style history-only builds, section 1 may hold only minimal title/review context or be empty if property identity is already clear in `AC_PROPERTY`.

### Section 2: Settings And Run Controls

Common Tauris rows:

- `WELLS <well-count-expression>`
- `BTU <value>`
- `ELOSS OPINC 0 NOH 0 1`
- `ELOSS PMAX`
- `LIFE <MM/yyyy>` for hard abandonment dates.

Builder notes:

- Use section 2 for run controls that affect the economic calculation rather than a phase forecast.
- If abandonment/capital creates a hard terminal date, add a `LIFE` row rather than burying the date in comments.
- Keep base controls unqualified unless source data explicitly scopes them.
- For sparse builds, do not invent `WELLS`, `BTU`, `ELOSS`, or `LIFE` unless they are required for a verified run workflow or supplied by source assumptions.

### Section 3: Reserved / Not Common In Current Tauris Output

The checked Tauris parser grammar does not expose a dedicated section 3 visitor in the common economic path. Treat section 3 as needs-verification before generating rows.

Builder notes:

- Do not invent section 3 lines.
- If a source ARIES database has section 3 rows, preserve and review them against that database.

### Section 4: Production, Forecasts, Loads, Formulas

Common Tauris rows:

- `START <MM/yyyy>`
- `*START ...` plus `START ... DELAY ...` for recompletion timing.
- Phase keywords such as `OIL`, `GAS`, `NGL`, `CND`, `WTR`.
- Ditto keyword `"` for continuation forecast segments.
- `LOAD MP.<PRODUCT> <PHASE> <start MM/yyyy> <end MM/yyyy> #/A`
- `ENDDATE <token-or-date-reference>`
- `TEXT <diagnostic or formula note>`

Forecast expression patterns:

- `<q_beg> <q_end> <unit> <duration> LOG TIME`
- `<q_beg> X <unit> <duration> EXP X`
- `X <q_end> <unit> X AD EXP <dmin>`
- `<q_beg> X <unit> <dmin> EXP B/<b> <decline>`
- `<q_beg> <q_end> <unit> <duration-or-date> B/<b> <decline>`

Builder notes:

- Use the phase keyword for the first segment of a product forecast; use `"` for continuation rows.
- Use `TAURIS` qualifier for generated forecasts unless a verified source qualifier should be preserved.
- Prefer `LOAD` when future monthly array data should be consumed directly instead of approximated with Arps.
- Preserve zero/invalid forecast cases as diagnostics unless a known cost-case fallback applies.
- Add `ENDDATE` when the generated forecast needs an explicit run-end anchor.
- Convert entry declines to ARIES-facing effective annual values according to the calculation reference before scripting final lines.
- For Enverus history-only input, historical production belongs in `AC_PRODUCT`/history tables, not automatically in section 4 forecast lines.
- Create section 4 forecast lines only when there is a forecast, a decline fit, a future monthly stream, or a user-approved forecast assumption.
- If the database is intended only to inspect history, leave section 4 empty or add a review note outside final economics.

### Section 5: Prices And Price Adjustments

Common Tauris row families:

- Price variable rows from product value/segment data.
- `PAJ/<phase>` for price adjustment.
- `PAD/<phase>` for price deduction/differential.
- Continuation rows using `"` for scheduled changes.

Common expression patterns:

- `0 X <unit> <MM/yyyy> AD PC 0`
- `<value> X <unit> TO LIFE PC 0`
- `<value> X <unit> <duration> IMO PC 0`

Builder notes:

- Add a zero/bootstrap line at the effective date when Tauris source behavior requires a scheduled value series.
- Use `PC 0` for flat escalation when the source has no escalation.
- Convert gallon-based differentials to barrel basis before writing.
- If product phase is unknown, do not map price rows to a guessed phase.
- Enverus production history normally does not imply a price deck. Leave section 5 empty unless a price deck or explicit pricing assumption is supplied.

### Section 6: Expenses, Taxes, Operating Costs

Common row families:

- Operating cost variables by phase or cost type.
- Severance/ad valorem/tax-style rows.
- Scheduled cost rows with `PC 0`.
- Continuation rows with `"`.

Builder notes:

- Use source units and variable mapping from Tauris.PhdWin before choosing keyword/unit.
- Use `TO LIFE` for final open-ended cost segments.
- Preserve cost exclusions and unsupported escalation as review diagnostics.
- Avoid combining unlike cost streams into one line just because they share timing.
- Do not infer LOE, taxes, gathering, or fixed costs from production history alone.
- For proforma shells, section 6 is commonly empty until a human supplies cost assumptions.

### Section 7: Ownership

Common Tauris rows:

- `NET <wi%> <oil-nri%> <gas-nri%> [npi%] % [reversion]`
- Ditto keyword `"` for continuation ownership or reversion lines.

Supported reversion trigger families seen in Tauris references:

- Net revenue / value thresholds.
- Elapsed years.
- Specified dates.
- Payout.
- Cumulative oil or gas.
- Investment-linked payout/net revenue.

Builder notes:

- Use group/partner qualifier for generated ownership lines.
- Append reversion conditions to the ownership expression; do not create unrelated rows.
- Date reversions should use `MM/yyyy AD`.
- Unsupported reversion types must become review risk rows, not silent drops.
- Enverus history feeds typically do not contain full ARIES ownership economics. Leave section 7 empty unless ownership interests and reversion terms are explicitly available.
- If ownership is known only as display metadata, keep it in property/reference fields rather than writing economic ownership lines.

### Section 8: Investments And Capital

Common Tauris patterns:

- Template-driven investment expressions.
- `DRILL`, `COMPL`, `CAPITAL`, `WRKOVR`, `INVEST` or source-template keyword.
- `<tangible> <intangible> <G-or-N> <schedule> PC 0`
- Schedule as `<MM/yyyy> AD` or `<months> MOS`.

Builder notes:

- Prefer expression templates from Tauris.PhdWin over handwritten capital syntax.
- Use partner qualifier for partner-specific capital.
- Use `TAURIS` for global generated capital/abandonment-style rows.
- If abandonment has a hard date, also create the section 2 `LIFE` row.
- Do not create drilling/completion/capital lines from well status, first-production date, or history alone.
- For Enverus proforma history databases, section 8 should usually remain empty unless capital assumptions are supplied.

### Section 9: Overlay, Stream Arithmetic, Derived Streams

Common Tauris patterns:

- Stream arithmetic such as `S/371`.
- Formula-derived phase/stream adjustments.
- Shrink or product formula rows that do not fit simple section 4 or section 5 line families.

Builder notes:

- Use section 9 for formula/overlay behavior where a derived stream is adjusted from another stream.
- PHDWin shrink may need conversion to residual shrink or overlay treatment depending on source variable type.
- If formula parser cannot identify the target phase/stream, add a `TEXT` diagnostic row and preserve source formula evidence.
- Do not derive shrink, yield, or stream arithmetic from raw oil/gas/water history unless the source explicitly includes those formulas or the user approves a calculation rule.

## Sparse Source Best Practices

When building ARIES Access databases from Enverus or other non-PHDWin sources:

- Separate structural validity from economic completeness.
- It is valid for all or most `AC_ECONOMIC` sections to be empty.
- `AC_PROPERTY`, project membership, `AC_PRODUCT`/history, sort/filter rows, and `AC_SCENARIO` can be sufficient for an inspectable ARIES database.
- Use `AC_SCENARIO` as a run/governance scaffold only; it does not require every section to have rows.
- Prefer an explicit `ACTIVE` scenario with known data qualifier rows only when a run path needs one.
- Do not backfill prices, costs, ownership, taxes, capital, or forecasts from missing data.
- Mark missing economics in external review notes or `TEXT` rows only when the operator needs to see the omission inside ARIES.
- For every non-empty section, record source evidence: file, column, calculation, assumption owner, and confidence.
- For every empty section, record the reason in the build summary: `not supplied`, `not applicable`, `deferred`, or `requires human assumption`.

Recommended sparse build summary:

| Section | State | Reason | Rows generated | Next data needed |
|---:|---|---|---:|---|
| 1 | Empty by design / Populated | Title metadata source | 0+ | Optional case labels |
| 2 | Empty by design | No run controls supplied | 0 | BTU, well count, econ limit controls |
| 4 | Empty by design / Populated | History only or approved forecast | 0+ | Forecast/deck/decline assumption |
| 5 | Empty by design | No price deck supplied | 0 | Price deck/differentials |
| 6 | Empty by design | No costs/taxes supplied | 0 | LOE, taxes, gathering |
| 7 | Empty by design | No ownership deck supplied | 0 | WI/NRI/reversions |
| 8 | Empty by design | No capital supplied | 0 | Capital schedule/templates |
| 9 | Empty by design | No formulas supplied | 0 | Shrink/yield/stream formulas |

## Incremental Case Best Practices

Incremental cases need extra discipline because they are usually dependent on a
base case, parent case, project membership, or an economic-difference grouping.
Do not treat an incremental as just another standalone property unless the source
explicitly says it is standalone.

Use these labels before scripting rows:

| Incremental status | Meaning |
|---|---|
| `Base case` | Standalone economic case or parent case. |
| `Incremental case` | Represents an economic delta, uplift, recompletion, workover, or group difference relative to another case. |
| `Needs dependency review` | Source suggests incremental behavior but parent/base relationship is missing or ambiguous. |

Builder rules:

- Preserve the relationship between the incremental and its base/parent in `AC_PROPERTY`, `PROJECT`, `PROJLIST`, build notes, or a governed reference field before scripting economics.
- Do not duplicate full base-case economics into an incremental unless the source explicitly stores a complete standalone incremental run.
- Use qualifiers to separate incremental scenarios or partner/group economics when the incremental is scenario-selected.
- Keep forecast, ownership, capital, and cost rows scoped to the incremental effect, not the entire parent case, unless source evidence says otherwise.
- For recompletions, preserve parent timing where known. Tauris forecast behavior may use `*START` plus `START ... DELAY ...` to preserve timing context.
- For workovers or uplift cases, include only the approved uplift forecast/cost/capital rows and avoid inferring unchanged base economics.
- For incremental monthly streams, prefer a `LOAD` row or history/load table strategy when the source provides future monthly volumes.
- For incremental capital, use partner/group qualifiers when capital ownership differs from the base case.
- For unresolved parent/base references, mark the case `Needs dependency review` and create review notes instead of writing final economics.
- Validate project membership so the incremental appears in the intended project/list and does not contaminate the base project accidentally.

Incremental review checklist:

| Check | Question |
|---|---|
| Identity | Is the case clearly marked as base, incremental, recompletion, workover, or group difference? |
| Parent/base | What base case does it depend on? Is that relationship represented in the export or build summary? |
| Forecast | Are production rows full-case values or incremental deltas? |
| Costs | Are costs incremental-only, full-case, or absent? |
| Ownership | Does the incremental use the same ownership as base, or a separate partner/group qualifier? |
| Capital | Is capital incremental-only and scheduled correctly? |
| Scenario | Which `AC_SCENARIO` qualifier selects the incremental rows? |
| Project | Does `PROJLIST` put the incremental in the intended project without duplicating the wrong case? |
| Run readiness | Can ARIES run the incremental without requiring hidden base-case assumptions? |

For sparse Enverus-style builds, incremental best practice is usually to preserve
incremental identity and project membership first. Do not create incremental
economics until the source provides or a human approves the delta forecast,
costs, ownership, and capital assumptions.

## Source-to-Builder Checklist

Before scripting final rows, ask Claude Cowork to build this inventory:

| Source area | Questions |
|---|---|
| Property/case | What `PROPNUM` is used? Is it in `AC_PROPERTY`? |
| Forecasts | Which product phases exist? Are forecasts Arps, monthly array, formula, or missing? |
| Production variables | Are there segment rows, product values, shrink, differentials, or formula-driven streams? |
| Prices/costs/taxes | Which units and escalation behavior are known? Which are unsupported? |
| Ownership | Which group/partner qualifiers exist? Are reversions present? |
| Capital | Which investment templates and schedules exist? Are partner qualifiers needed? |
| Scenarios | Which `AC_SCENARIO.DATA_SECT` rows select which qualifiers? |
| Sidefiles/lookups | Are `SIDEFILE`, `FILE`, `LOOKUP`, or macros present? Can they be resolved? |

For non-PHDWin sources, add:

| Source area | Questions |
|---|---|
| History | Which table/file carries monthly or daily oil, gas, water, days, pressures, and well counts? |
| Provenance | What source database/file name should be carried into `SRC_DB` or build metadata? |
| Forecast assumption | Is there an actual forecast, or only historical production? |
| Economics assumption | Did a human provide prices, costs, ownership, taxes, or capital, or are they intentionally absent? |
| ARIES usability | Is the goal to open/filter/inspect properties, or to run economics? |

## Output Format For Claude Cowork

Ask for a dry-run table before any file/database write:

| PROPNUM | SECTION | SEQUENCE | QUALIFIER | KEYWORD | EXPRESSION | Source evidence | Confidence | Notes |
|---|---:|---:|---|---|---|---|---|---|

Confidence values:

- `Verified Tauris`: directly grounded in Tauris.PhdWin code behavior.
- `CHM-supported`: consistent with ARIES docs but not directly generated in the checked code path.
- `Needs verification`: inferred from source data or prior examples; require a known-good ARIES export or app validation before mutation.

## Validation Before Export

- Every row has `PROPNUM`, `SECTION`, `KEYWORD`, and `EXPRESSION`.
- `SEQUENCE` is contiguous by `PROPNUM + SECTION`.
- Rows are sorted by `PROPNUM`, `SECTION`, `SEQUENCE`.
- Blank qualifier rows are retained.
- Scenario-selected qualified rows are not merged incorrectly.
- `SIDEFILE`, `LOOKUP`, and macro rows are resolved or preserved with `TEXT` diagnostics.
- Unsupported formulas, reversions, units, or escalation methods are visible in review output.
- `AC_SCENARIO` includes the data sections needed by the selected run scenario.
- The generated row set is tested by opening the `.accdb` in ARIES or comparing against a known-good export when available.

## Do Not Do

- Do not assume all expressions have seven tokens.
- Do not hard-code one qualifier across all sections without checking `AC_SCENARIO`.
- Do not drop unsupported source rows.
- Do not invent phase keywords, stream numbers, reversion syntax, or investment templates.
- Do not write directly to an ARIES database without a dry-run row table and human approval.
