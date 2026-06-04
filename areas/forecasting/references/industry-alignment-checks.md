# Industry Forecasting Alignment Checks

This is not a formal compliance standard. Use it as a petroleum-engineering sanity check so limited-data auto-forecasting stays directionally aligned with accepted decline-curve practice.

## Positioning

The Tauris forecasting workflow is empirical decline-curve analysis and data-quality review. It is not a reservoir simulator, pressure-transient analysis, material-balance calculation, or reservoir-simulation benchmark.

When reservoir, PVT, completion, flowing bottomhole pressure, and operating detail are missing, the workflow should:

- state the input limitations
- treat results as limited-data production forecasting
- prefer candidate curves and QC reasons over a silent single answer
- route ambiguous wells to human review

## Alignment Checks

Use these checks before trusting an automated projection.

### 1. Decline Convention

Internal nominal decline parameters must not be exported directly to commercial forecast-entry screens that expect effective annual decline.

Expected export behavior:

- pin model time to years
- convert initial nominal Arps decline to effective secant annual decline
- convert terminal nominal exponential decline to effective annual exponential decline

### 2. Forecast Origin

Do not assume first production is the correct forecast origin.

Flag wells with:

- recompletion/stimulation response
- pump swap or artificial-lift change
- shut-in/restart cleanup
- frac hit or offset-completion response
- choke/facility/lift constraints
- multiple sustained rate uplifts

Each candidate origin should be tested or reviewed.

### 3. Pressure/Rate Consistency

Use pressure as context and QC, not as an automatic physics model.

Common interpretations:

- rate down + pressure down: depletion-supported decline
- rate down + pressure flat/up: possible constraint or operational issue
- rate up + pressure down: drawdown change, stimulation, recompletion, or cleanup response
- rate flat + pressure down: hidden depletion risk
- volatile rate + volatile pressure: unstable operations

### 4. Method Eligibility

Do not run every method on every well.

Examples:

- daily production with usable pressure can support pressure-aware residual diagnostics
- monthly production should favor simpler reserves-style decline fitting
- sparse histories should stay yellow/red QC
- missing pressure should disable pressure-aware hybrid methods

### 5. History-Window Sensitivity

Where enough data exists, compare fit behavior across history windows such as:

- 30 days
- 90 days
- 180 days
- 360 days
- full usable history

Large movement in projected rate, decline, or EUR across windows should raise QC.

### 6. Visual Sanity

Use an engineering-style log-rate plot for review. The final visual target is:

```text
areas/forecasting/assets/engineering_log_decline_plot_reference.png
```

The reviewer should be able to see:

- historical phase behavior
- forecast start / time zero
- forecast trend
- pressure context when available
- regime changes or event markers

## Output Wording

Use language like:

```text
This forecast is aligned with limited-data empirical DCA review, but it is not a full reservoir-engineering calculation or benchmark result.
```

Avoid:

```text
formally compliant
certified
Reservoir-simulation validated
Physics-complete
```
