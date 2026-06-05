# AC_ECONOMIC Line Grammar

This is the operational grammar Claude Cowork should use for Tauris ARIES `AC_ECONOMIC` line drafting and review. It is based on Tauris.PhdWin conversion methods, extracted `ARIES_UG001.chm` economics help, and checked-in Tauris skill docs.

## Certainty Labels

- **Verified Tauris**: implemented in the Tauris conversion code path.
- **CHM-supported**: supported by the ARIES user-guide concepts/appendices.
- **Inferred**: reasonable from Tauris code and ARIES context, but needs a real ARIES example before final mutation.

## Table Row Contract

Every row is:

```text
PROPNUM | SECTION | SEQUENCE | QUALIFIER | KEYWORD | EXPRESSION
```

Rules:

- `PROPNUM`: property/case id.
- `SECTION`: numeric economic section; it changes grammar meaning.
- `SEQUENCE`: contiguous row order within each section after expansion.
- `QUALIFIER`: blank means always active; nonblank is scenario-selected.
- `KEYWORD`: ARIES keyword or ditto keyword `"`.
- `EXPRESSION`: fixed-position line body for the keyword/section.

Final output must sort by `PROPNUM`, `SECTION`, `SEQUENCE`; then resequence each section contiguously.

## Sections

Use these section numbers unless a source ARIES database proves otherwise:

| Section | Name | Common generated keywords |
|---:|---|---|
| 1 | Misc/title | `TITLES` |
| 2 | Settings / production controls | `WELLS`, `BTU`, `ELOSS`, `LIFE`, `ABANDON`, `SHRINK` |
| 4 | Production / forecast | `START`, `*START`, `OIL`, `GAS`, `NGL`, `CND`, `WTR`, `LOAD`, `ENDDATE`, formula stream lines |
| 5 | Prices | `PRI/OIL`, `PRI/GAS`, `PRI/NGL`, `PRI/CND`, `PAJ/<phase>`, `PAD/<phase>` |
| 6 | Expenses / taxes | `OPC/<phase>`, `LTC/OLC`, `GTC/GAS`, `STD/<phase>`, `STX/<phase>`, `ATX`, `ABEX`, `SALVEX` |
| 7 | Ownership | `NET`, `"` |
| 8 | Investments | `DRILL`, `COMPL`, `CAPITAL`, `WRKOVR`, `INVEST` |
| 9 | Overlay | stream arithmetic such as `S/371` and formula results |

## Qualifier Grammar

Scenario selection is section-specific:

1. For each scenario data section, check qualifiers in scenario order.
2. Use the first qualifier that has rows for `PROPNUM + SECTION`.
3. Also include blank/null qualifier rows in that section.
4. Do not combine multiple nonblank qualifiers in the same section unless explicitly requested as a sensitivity merge.

Generated Tauris lines typically use:

- blank qualifier for base/control lines
- `TAURIS` for generated forecast/formula/global lines
- group or partner qualifier for ownership/capital lines

## Expression Length Rule

Do not treat seven tokens as universal. ARIES `EXPRESSION` is keyword/section-specific and can be shorter or longer depending on the line family.

Tauris forecast templates are fixed-position expressions. Several common forecast rows use six expression fields; terminal-Dmin switch rows commonly use seven. Other sections, such as titles, controls, ownership, investments, sidefiles, lookups, and overlay formulas, use their own field counts.

Review the grammar by `SECTION + KEYWORD`, not by token count alone.

## Forecast Expression Grammar

Forecast expressions live in section 4. The first row for a product uses the phase keyword; continuation rows use `"`.

Common phase keywords:

- `OIL`
- `GAS`
- `NGL`
- `CND`
- `WTR`

### Common Decline Segment Forms

These forms are **Verified Tauris** templates. The expression body is fixed-position.

| Purpose | Expression form |
|---|---|
| log/time ratio or decline fit | `<q_beg> <q_end> <unit> <duration> LOG TIME` |
| exponential with final value solved | `<q_beg> X <unit> <duration> EXP X` |
| exponential with beginning value solved | `X <q_end> <unit> <duration> EXP X` |
| hyperbolic/Arps with b-factor and decline | `<q_beg> <q_end> <unit> <duration-or-date> B/<b> <decline>` |
| volume/end-date constrained | `<q_beg> X <unit> <remaining-volume> <volume-unit> B/<b> <decline>` |

`X` means ARIES should solve or ignore that position according to the keyword/section context.

### Terminal Dmin Switch Forms

When the source segment has terminal decline (`Declmin` / Dmin), Tauris emits terminal-switch-style rows. These are important fixed-position forms that often have seven expression fields:

```text
<q_beg> X <unit> <dmin> EXP B/<b> <decline>
X <q_end> <unit> X AD EXP <dmin>
```

Interpretation:

- First line: hyperbolic/Arps-style segment with b-factor and initial decline, capped by terminal exponential decline.
- Second line: terminal exponential continuation to the solved/target endpoint.
- `B/<b>` is the Arps b-factor token.
- `<decline>` should be the commercial-app entry decline after convention conversion.
- `<dmin>` should be the effective annual terminal exponential decline after convention conversion.

Where exact ARIES parser behavior is uncertain, keep both lines together and flag as terminal-Dmin paired expression. Do not reject shorter expressions elsewhere simply because they have fewer than seven fields.

## Ratio-Line Form

Ratios are generated in section 4 using the ratio product phase keyword first, then `"` continuation lines.

Tauris ratio expression:

```text
<ratio_start> <ratio_end> <ratio_unit> <duration> LOG TIME
```

Known ratio mappings:

| Ratio | Numerator / denominator | Common unit |
|---|---|---|
| `GOR` | gas / oil | `M/B`, `MM/B`, or denominator-derived gas-per-barrel unit |
| `WOR` | water / oil | `B/B` |
| `WGR` | water / gas | `B/M` or `B/MM` |
| `Yield`, `NGL Yield` | NGL or condensate / gas | `B/M`, `B/MM`, or equivalent |
| `CND/GAS` | condensate / gas | `B/M`, `B/MM`, or equivalent |

Pick units from source forecast numerator/denominator units when present. If denominator unit starts with `MM`, preserve `MM` in the denominator token.

## Date And Duration Tokens

Use these tokens:

- `MM/yyyy AD`: absolute date.
- `<n> IMO`: incremental months.
- `<n> MOS`: months from start/effective date where source scheduling uses offsets.
- `<n> YR` or `YRS`: years.
- `TO LIFE`: continue to economic life.
- `X AD`: solve/use endpoint date position.

Dates generated by Tauris use `MM/yyyy`.

## Units

Production/rate units from ARIES CHM appendices and Tauris conversion:

- oil/liquids/water rates: `B/D`, `B/M`, `B/Y`, `MB/D`, `MB/M`, `MB/Y`
- gas rates: `M/D`, `M/M`, `M/Y`, `MM/D`, `MM/M`, `MM/Y`
- ratio units: `M/B`, `MM/B`, `B/M`, `B/MM`, `B/B`, `M/M`, `U/B`, `U/M`
- price/cost units: `$/B`, `$/M`, `$/M` for fixed monthly style costs, `%`
- capital units are normally implicit in investment expressions; preserve template units.

Conversions used by Tauris:

- `scf` -> `Mcf` with multiplier `0.001`
- `gal` -> `Bbl` with multiplier `1/42`
- shrink percent -> residual shrink fraction `1 - shrink_percent`

## LOAD Lines

For future monthly array forecasts:

```text
KEYWORD = LOAD
EXPRESSION = MP.<PRODUCT> <PHASE> <start MM/yyyy> <end MM/yyyy> #/A
QUALIFIER = TAURIS
SECTION = 4
```

Use this when the forecast should be loaded from monthly production/forecast rows instead of recreated as an Arps equation.

## Formula / Overlay Lines

Formula parser output should be written as ARIES expressions using the target phase keyword in section 4 or stream keyword in section 9.

If a formula cannot be parsed:

- add a `TEXT` diagnostic line
- do not invent a replacement expression
- preserve the source formula in review notes

## Ownership Lines

Section 7 ownership uses:

```text
NET <working-interest-%> <oil-revenue-interest-%> <gas-revenue-interest-%> [npi-%] % [reversion-trigger...]
"   <working-interest-%> <oil-revenue-interest-%> <gas-revenue-interest-%> [npi-%] % [reversion-trigger...]
```

Supported reversion trigger forms from Tauris:

- `<value> M$N`
- `<value> YR`
- `<MM/yyyy> AD`
- `<value> M$/747+1186`
- `1 PAYOUT`
- `0 PAYOUT`
- `<value> MB`
- `<value> MMF`

Use group qualifier for generated ownership lines.

## Investment Lines

Template form:

```text
<tangible> <intangible> <G-or-N> <schedule> PC 0
```

Common keywords:

- `DRILL`
- `COMPL`
- `CAPITAL`
- `WRKOVR`
- `INVEST`

Schedules:

- `<MM/yyyy> AD`
- `<months> MOS`

Use partner qualifier unless the generated investment is a Tauris/global line such as abandonment.

## Validation Checklist

Before writing or exporting:

- no missing `PROPNUM`, `SECTION`, `KEYWORD`, or `EXPRESSION`
- sequences are contiguous by `PROPNUM + SECTION`
- no unintended duplicate effective rows
- blank qualifier rows are retained
- scenario-selected qualifier rows are not merged incorrectly
- sidefile/lookup/macro failures are preserved with `TEXT` and commented source rows
- terminal-Dmin paired rows are kept together
- expression token count is checked against the keyword/section family, not against a universal length
- nominal decline values are not written where effective annual values are required
