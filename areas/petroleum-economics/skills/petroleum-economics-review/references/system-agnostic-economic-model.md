# System-Agnostic Petroleum Economic Model

This model describes petroleum economics without depending on a specific system, database, or table layout.

It is informed by the common concepts used in PHDWin and ARIES workflows, but the concepts below should also apply to spreadsheets, reserves systems, custom databases, and CSV exports.

## Concept Map

| Neutral concept | Business meaning | Common source-system signals |
|---|---|---|
| Economic case | The evaluated unit of economics | lease, property, well, case, scenario, group, project |
| Property identity | Stable name and key for a case | lease ID, property number, case ID, display name |
| Product stream | Product-specific volumes and values | oil, gas, NGL, water, product codes |
| Historical production | Actual dated production before forecast | monthly history, daily/test history, cumulative volumes |
| Forecast segment | Ordered forecast interval or curve segment | forecast rows, segment arrays, decline parameters |
| Price deck | Product pricing and realizations | price table, scenario price, differential, escalation |
| Ownership tranche | Economic ownership over time or condition | WI, NRI, royalty, burden, payout, reversion |
| Cost stream | Recurring operating economics | LOE, fixed cost, variable cost, transportation, processing |
| Capital event | Non-recurring investment or abandonment | capex, investment, drilling, completion, facilities, ARO |
| Fiscal rule | Taxes and fiscal deductions | severance, ad valorem, income tax, local fees |
| Scenario | Alternative economic assumption set | case, model, deck, scenario, sensitivity |
| Group/project | Collection or rollup of cases | project, project list, saved group, member list, seller view |
| Economic output | Calculated economics | cash flow, NPV, payout, IRR, reserves, revenue, net cash flow |

## Cross-System Review Principle

When comparing systems, review whether the economic meaning survived, not whether the table names match.

Good review questions:

- Does each source economic case map to one intended reviewed case?
- Are grouped or incremental cases represented as economics, not just labels?
- Are product streams complete and consistently named?
- Does history end before forecast begins?
- Are forecast segments ordered and dated correctly?
- Do WI, NRI, royalty, and burden relationships reconcile?
- Are capital and expenses in the right period and sign convention?
- Are taxes applied to the intended revenue or value base?
- Are scenario and price assumptions explicit?
- Can the reported NPV and cash flow be traced back to source assumptions?

## Minimum Review Packet

A useful review packet should include:

- case/property inventory
- product inventory
- forecast summary by case and product
- historical production summary, when available
- ownership summary by case/group/scenario
- price deck or price assumptions
- expense and capital summary
- tax/fiscal assumptions
- group/project membership
- output summary with NPV date and discount rate

## Conversion-Aware Checks

Use these checks when one system is being compared to another:

- Identity: source ID, target ID, and display name line up.
- Membership: groups/projects preserve intended member cases.
- Volumes: gross and net volumes reconcile within stated tolerance.
- Timing: first production, forecast start, capex dates, and effective date are consistent.
- Ownership: WI/NRI and burdens reconcile after conversion.
- Products: product mapping does not drop minor products or confuse gas/NGL logic.
- Costs: fixed, variable, product-linked, and one-time costs are not merged incorrectly.
- Taxes: tax basis and timing are explicit.
- Outputs: cash flow deltas are explained by known assumptions, not silent data loss.
