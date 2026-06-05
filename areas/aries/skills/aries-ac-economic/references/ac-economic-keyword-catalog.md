# AC_ECONOMIC Keyword Catalog

This is a curated Tauris keyword catalog for drafting and reviewing ARIES `AC_ECONOMIC` rows. It is not a complete vendor catalog; use `ARIES_UG001.chm` or a supplied ARIES database for exhaustive keyword verification.

## Control And Text Keywords

| Keyword | Section | Use |
|---|---:|---|
| `TITLES` | 1 | Title/case marker rows. |
| `TEXT` | any | Human-readable diagnostic/comment row. |
| `"` | current section | Continuation/ditto keyword for the prior line family. |
| `SIDEFILE` | source section | Sidefile indirection. Resolve before final interpretation. |
| `LOOKUP` | source section | Lookup indirection. Resolve before final interpretation. |
| `START` | 4 | Forecast/economics start date. |
| `*START` | 4 | Commented/diagnostic start marker, used by Tauris recompletion handling. |
| `ENDDATE` | 4 | Generated run end-date marker. |
| `LOAD` | 4 | Load future monthly values from table rather than recreate an equation. |

## Phase Keywords

| Keyword | Phase |
|---|---|
| `OIL` | oil production |
| `GAS` | gas production |
| `NGL` | natural gas liquids |
| `CND` | condensate |
| `WTR` | water |
| `OGW` | combined oil/gas/water cost phase |
| `T` | total/fixed cost phase |

## Production Controls

| Keyword | Section | Notes |
|---|---:|---|
| `WELLS` | 2 | Well count/phase control. Tauris writes `0 1` for oil-major and `1 0` for gas-major unless cost-case logic overrides. |
| `BTU` | 2 | Gas BTU value; Tauris default is `1000` when missing. |
| `ELOSS` | 2 | Economic loss/economic limit behavior. Tauris uses `OPINC 0 NOH 0 1` or `PMAX` depending on case context. |
| `LIFE` | 2 | Economic life override/date. Used for some abandonment/cost-case handling. |
| `SHRINK` | 2 | Shrink control; Tauris uses residual shrink logic where applicable. |
| `ABANDON` | 2 | Abandonment schedule/control when generated from investment templates. |

## Prices

| Keyword | Section | Unit / use |
|---|---:|---|
| `PRI/OIL` | 5 | oil price, commonly `$/B` |
| `PRI/GAS` | 5 | gas price, commonly `$/M` |
| `PRI/NGL` | 5 | NGL price, commonly `$/B` |
| `PRI/CND` | 5 | condensate price, commonly `$/B` |
| `PRI/WTR` | 5 | water price, commonly `$/B` |
| `PAJ/OIL` | 5 | oil price adjustment/escalation |
| `PAJ/GAS` | 5 | gas price adjustment/escalation |
| `PAJ/NGL` | 5 | NGL price adjustment/escalation |
| `PAJ/CND` | 5 | condensate price adjustment/escalation |
| `PAD/OIL` | 5 | oil price deduction/differential |
| `PAD/GAS` | 5 | gas price deduction/differential |
| `PAD/NGL` | 5 | NGL price deduction/differential |
| `PAD/CND` | 5 | condensate price deduction/differential |

## Costs And Taxes

| Keyword | Section | Unit / use |
|---|---:|---|
| `OPC/OGW` | 6 | combined operating cost |
| `OPC/T` | 6 | fixed/total operating cost |
| `OPC/OIL` | 6 | oil operating cost |
| `OPC/GAS` | 6 | gas operating cost |
| `OPC/NGL` | 6 | NGL operating cost |
| `OPC/WTR` | 6 | water operating cost |
| `LTC/OLC` | 6 | oil transportation / lease transport cost |
| `GTC/GAS` | 6 | gas transportation cost |
| `STD/OIL` | 6 | oil severance tax amount/deduction |
| `STD/GAS` | 6 | gas severance tax amount/deduction |
| `STD/NGL` | 6 | NGL severance tax amount/deduction |
| `STD/CND` | 6 | condensate severance tax amount/deduction |
| `STX/OIL` | 6 | oil severance tax percent |
| `STX/GAS` | 6 | gas severance tax percent |
| `STX/NGL` | 6 | NGL severance tax percent |
| `STX/CND` | 6 | condensate severance tax percent |
| `ATX` | 6 | ad valorem tax |
| `ABEX` | 6 | abandonment expense |
| `SALVEX` | 6 | salvage expense |

## Ownership

| Keyword | Section | Use |
|---|---:|---|
| `NET` | 7 | First ownership line for a qualifier/group. |
| `"` | 7 | Continuation ownership/reversion line. |

Ownership expression fields:

```text
<working-interest-%> <oil-revenue-interest-%> <gas-revenue-interest-%> [npi-%] % [reversion-trigger]
```

## Investments

| Keyword | Section | Use |
|---|---:|---|
| `DRILL` | 8 | drilling capital |
| `COMPL` | 8 | completion capital |
| `CAPITAL` | 8 | generic capital |
| `WRKOVR` | 8 | workover capital |
| `INVEST` | 8 | generic investment |

Common investment expression:

```text
<tangible> <intangible> <G-or-N> <schedule> PC 0
```

## Overlay / Streams

| Keyword | Section | Use |
|---|---:|---|
| `S/<stream-number>` | 9 | Direct stream arithmetic/assignment. |
| phase keyword | 4 or 9 | Formula parser output may target product phase streams. |

Overlay expressions often include arithmetic operators, stream references, `TO LIFE`, `PLUS`, and other parser-specific tokens. Preserve exact generated expression text.

## Keyword Use Rules

- Do not invent a keyword when a Tauris mapping exists.
- If a keyword is absent from this catalog but present in a supplied ARIES DB, preserve it and mark it verified-by-source.
- If a keyword is absent from both this catalog and source data, mark it unverified.
- Preserve casing and punctuation for keywords such as `PRI/OIL`, `S/371`, and `"`.
