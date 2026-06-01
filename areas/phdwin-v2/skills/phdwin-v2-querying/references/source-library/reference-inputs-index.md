# Reference Inputs Index

This index points the skill at the user-provided reference library under the local `docs/reference-inputs` folder.

Use these files as the domain documentation set of record when the checked-in code alone is not enough.

## Extraction And Table Layout

- `00.PHDWin Table Requirments.xlsx`
  - use for expected table coverage and required table inventory
- `2021-03-23 PHDWin Datamodel.pdf`
  - use for broader data-model interpretation
- `PHDWin_v2_tables.accdb`
  - use for concrete table inspection if the task is about table/field structure
- internal Aries reference database
  - use as a reference Access dataset when checking surfaced tables and naming, when the user provides one locally

## PhdWIN Product Behavior

- `PHDWin User Manual.pdf`
  - use for product terminology and user-facing workflow behavior
- `phdwin.chm`
  - use for legacy product help content if needed

## Forecasting / Decline / Economics

- `PHDWin Arps Decline Documentation.pdf`
  - use for decline-method interpretation
- `Aries_Arps Forcast Methods.pdf`
  - use for ARPS/forecast comparison context
- `PHDWin Sample ARPs Calculations.xls`
  - use for sample decline calculations
- `PHDWin Discounting Example -.xlsx`
  - use for discounting/economics examples
- `PHD Working Interest Reversion Modelling.pdf`
  - use for ownership/reversion interpretation

## PhdWIN Output Definitions

- `PHDWinOut.mdb`
  - use for output-oriented data structures
- `Phdwinout definitions_complete.xls`
  - use for output field definitions
- `PHDWin_Outputs.xlsx`
  - use for output examples

## PhdWIN To ARIES Conversion

- `2023.05.15 - PHDWin to Aries  Revisions_v2.docx`
  - use for conversion revisions and open mapping details
- local PHDWin vs Aries notes
  - use for comparison notes and mapping logic
- local Aries to PHDWin notes
  - use for reverse-direction mapping context
- `PHD Aries Decline Curve Conversions.xlsx`
  - use for decline conversion details between systems
- `ARIES Software Fundamentals Release 5000.12.1.pdf`
  - use for ARIES-side terminology when the task crosses systems
- `Aries_Template.accdb`
  - use for ARIES-side structure examples

## Working Rule

When answering a question, prefer this order of evidence:

1. generated entities and server code in the local PhdWIN implementation
2. `docs/PHDWIN_DATA_MAP.md` and other checked-in markdown docs
3. the reference-inputs library above for domain interpretation, comparison logic, and table meaning

If a conclusion comes mainly from the reference-inputs library rather than code, say so explicitly.
