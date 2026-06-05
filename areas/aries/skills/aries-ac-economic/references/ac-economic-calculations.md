# AC_ECONOMIC Calculations

Use this reference before writing forecast, ratio, and terminal-decline values into ARIES `AC_ECONOMIC`.

## Decline Convention

Tauris fitters may solve Arps in nominal decline per day/month/year. ARIES-style forecast entry should receive commercial app entry values:

- initial decline: effective secant annual decline
- terminal decline/Dmin: effective annual exponential decline

Always pin the time basis to years before export.

Use the forecasting MCP tool when available:

```text
convert_decline_convention(nominal_di, b_factor, terminal_dmin, input_time_unit)
```

Equivalent formulas:

```text
Di_nominal_annual = Di_nominal_input * periods_per_year
Dmin_nominal_annual = Dmin_nominal_input * periods_per_year
```

For exponential (`b = 0`):

```text
initial_effective_annual = 1 - exp(-Di_nominal_annual)
```

For hyperbolic (`b > 0`):

```text
initial_effective_secant_annual = 1 - (1 + b * Di_nominal_annual)^(-1 / b)
```

For terminal Dmin:

```text
terminal_effective_annual = 1 - exp(-Dmin_nominal_annual)
```

Do not write nominal `Di` or nominal `Dmin` directly into ARIES forecast expressions unless a verified ARIES parser example proves the target field expects nominal values.

## Dmin Terminal Switch

When a forecast uses hyperbolic decline with terminal minimum decline:

1. Write the first expression with `B/<b>` and the effective annual initial decline.
2. Write the paired terminal expression with `EXP <terminal_effective_annual>`.
3. Keep both rows adjacent in section 4.
4. Use the ditto keyword `"` for the paired/continuation row when it is continuing the same product phase.

Tauris verified terminal-switch shapes:

```text
<q_beg> X <unit> <dmin_eff> EXP B/<b> <di_eff>
X <q_end> <unit> X AD EXP <dmin_eff>
```

These examples often have seven expression fields, but seven is not a universal AC_ECONOMIC requirement. If exporting monthly-DCA b=0 + Dmin, use:

- `b = 0`
- initial effective annual exponential decline for `di_eff`
- terminal effective annual exponential decline for `dmin_eff`
- avoid hyperbolic `B/<b>` semantics unless the target line form requires the b token

## Ratio Math

Calculate ratios from rates using consistent units before formatting the ARIES expression.

Common definitions:

```text
GOR = gas_rate / oil_rate
WOR = water_rate / oil_rate
WGR = water_rate / gas_rate
NGL Yield = ngl_rate / gas_rate
CND/GAS = condensate_rate / gas_rate
```

Only calculate a ratio when denominator rate is positive. If denominator is zero or missing:

- do not emit a calculated ratio row
- add a review warning or `TEXT` diagnostic when needed

## Ratio Forecast Shape

Use ratio start/end values from the fitted ratio model:

```text
<ratio_start> <ratio_end> <ratio_unit> <duration> LOG TIME
```

Use a flat ratio by setting start and end equal. Use a two-stage ratio by writing an initial trend row followed by a flat continuation row.

## Unit Conversion

Before calculating ratios or forecast expressions:

- convert `scf` to `Mcf`: multiply by `0.001`
- convert gallons to barrels: multiply by `1/42`
- preserve `MM` denominator units when the source denominator is MMCF
- use `B` for barrels and `M` for Mcf in compact ARIES ratio units

## Rate Floors

ARIES expressions sometimes require nonzero rates where the source fit has zero. Tauris uses a small positive floor for generated expressions.

Use a small floor only for grammar/runtime compatibility. Do not let the floor change EUR or reserves calculations without explicitly documenting it.

## Date And Duration Calculations

Use:

- segment start: `MM/yyyy AD`
- segment duration: rounded whole incremental months as `<n> IMO`
- open final segment: `TO LIFE`
- recompletion delay: parent end-date marker plus `DELAY <months>`

When converting days to months, Tauris uses month-scale rounding for generated schedules. Keep the source date in diagnostics if rounding affects material timing.

## QC Notes

Flag these as Yellow/needs review:

- terminal Dmin line generated from inferred rather than verified target convention
- ratio denominator has sparse/zero history
- large unit conversion applied
- source monthly forecast conflicts with generated Arps expression
- effective annual decline exceeds plausible engineering bounds
- b-factor, Dmin, or ratio method differs from selected forecasting method
