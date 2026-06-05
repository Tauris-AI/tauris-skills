---
name: petroleum-economics-review
description: "Use only for system-agnostic petroleum economics reasonableness review: forecasts, price decks, ownership, costs, capital, taxes, reserves, cash flow, and economics QA after data has already been extracted or normalized. Do not use for PHDWin extraction, PHDWin-to-Aries conversion, ARIES Access contracts, or ARIES economic-line editing; use the PHDWin and ARIES skills first for those."
---

# Petroleum Economics Review

Use this skill for structured review of petroleum engineering economic inputs and outputs across systems.

This skill is intentionally system agnostic. It uses the common concepts shared by systems such as PHDWin and ARIES, but it should not require a PHDWin table, ARIES Access table, or specific vendor format unless the user provides one.

If the task is source-system work, route away from this skill:

- PHDWin source extraction, table discovery, SQLite export, or `.phz/.phd/.mod` handling belongs in `phdwin-v2-querying`.
- PHDWin-to-Aries conversion, ARIES Access export review, project/filter/sort mapping, and table-contract QA belongs in `aries-core`.
- `AC_ECONOMIC` line interpretation or editing belongs in `aries-ac-economic`.

Use this skill only after source-specific facts are already available and the user needs an economic/reviewer judgment layer.

## Core Economic Model

Normalize every review into these concepts before discussing source-system details:

- economic case: one evaluated property, well, lease, scenario, group, or incremental case
- property identity: source ID, display name, reserve class/category, operator, area, and reporting attributes
- product stream: oil, gas, NGL, water, or other product-specific volume/value stream
- forecast segment: start date, method, rate, decline, limit, product, and segment order
- historical production: dated actual volumes and tests used to anchor forecasts
- price deck: product prices, differentials, escalation, realizations, shrink, yield, and BTU assumptions
- ownership tranche: WI, NRI, royalty/burden, payout/reversion, and effective dates
- operating cost stream: fixed, variable, workover, transportation, processing, compression, gathering, and other recurring costs
- capital event: drilling, completion, facilities, recompletion, abandonment, and timing
- fiscal/tax rule: severance, ad valorem, income, fee, and jurisdiction-specific assumptions
- scenario: deterministic case, sensitivity, price/cost/ownership variant, or forecast case
- group/project: collection of economic cases used for rollups, incrementals, seller views, partner views, or reporting packages
- economic output: cash flow, reserves, revenue, expenses, taxes, capex, net cash flow, NPV, payout, rate of return, and sensitivities

## Workflow

1. Identify the review unit:
   - asset, well, lease, property, project, group, or portfolio
   - source system if known
   - effective date and forecast start date
   - case/scenario name
   - business question
2. Convert the source data into the core economic model above.
3. Separate source inputs, transformations, calculated outputs, and reviewer assumptions.
4. Check identity and grouping:
   - duplicate or missing property IDs
   - reserve class/category consistency
   - group/project membership and incrementals
   - scenario names and effective dates
5. Check volume logic:
   - history-to-forecast handoff
   - product coverage
   - forecast segment ordering
   - decline method and limits
   - EUR/cumulative volume reasonableness
6. Check value logic:
   - price deck and differentials
   - product-specific realizations
   - gas shrink, NGL yield, BTU, and plant assumptions
   - escalation and timing conventions
7. Check ownership:
   - WI/NRI relationship
   - burdens and royalties
   - payout or reversion logic
   - ownership by group/project/scenario
8. Check costs, capital, and fiscal assumptions:
   - fixed and variable LOE
   - product-linked costs
   - capital timing and classification
   - abandonment and future development costs
   - tax treatment and effective dates
9. Check outputs:
   - gross vs net volume consistency
   - revenue, cost, tax, and capex rollups
   - cash flow signs
   - NPV date and discount rate
   - payout, rate of return, and sensitivity behavior
10. Produce findings by severity with evidence, assumptions, and recommended next checks.

## PHDWin / ARIES Composite Guidance

Use these as conceptual signals, not hard dependencies:

- PHDWin often exposes source concepts as lease/case identity, ownership rows, groups/lists, forecast rows, monthly history, product names, economics, investment, filters, and sorts.
- ARIES often exposes target concepts as property records, ownership, product streams, economic lines, project/project-list membership, selection filters, sort filters, setup data, scenarios, and lookups.
- A good system-agnostic review should ask whether the same economic meaning survives across both models:
  - property/case identity is stable
  - product streams are complete
  - group/project membership is intentional
  - forecast segments retain their order and timing
  - history is not confused with forecast
  - WI/NRI and burden logic reconcile
  - capital and expense streams keep their signs and timing
  - economic outputs can be explained from the inputs

## Output Format

Prefer this structure:

1. Scope reviewed
2. Source data available
3. Normalized economic model
4. Findings by severity
5. Reconciliation checks
6. Open assumptions
7. Recommended next actions

Use severity labels:

- Critical: likely changes economic conclusions or prevents reliance
- High: material risk needing SME review
- Medium: unresolved assumption or incomplete mapping
- Low: cleanup, documentation, or presentation issue

## Guardrails

- Do not assume source-system field names imply the same business meaning across systems.
- Do not treat this skill as a source of ARIES or PHDWin vendor behavior.
- Do not copy from or summarize proprietary vendor help files, manuals, or uncommitted local reference inputs.
- Do not treat missing optional data as fatal without explaining the economic impact.
- Do not invent decline, ownership, tax, or price assumptions when source evidence is missing.
- Keep write-back or conversion recommendations separate from review findings.
- Use synthetic examples or scrubbed data in public artifacts.
- When reviewing converted data, compare economic meaning, not just table/field presence.

## References

- `references/review-checklist.md`: reusable economics review checklist.
- `references/system-agnostic-economic-model.md`: normalized concept model derived from common PHDWin and ARIES economic workflows.
