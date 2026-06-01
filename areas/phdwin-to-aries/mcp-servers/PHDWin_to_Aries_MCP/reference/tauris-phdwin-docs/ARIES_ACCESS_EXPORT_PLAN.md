# Aries Access Export Plan

## Purpose

This document defines the first implementation target for `Aries Access DB` export from the local `Tauris.PhdWin` import harness.

The current codebase already has two important pieces:

- a `PHDWin Access DB (as-is)` writer that can copy an Access template and populate tables from staged workspace data
- an `Aries` export layer that can already produce Aries-oriented datasets and JSON bundles

What does **not** exist yet is the actual `.accdb` population path for the Aries template.

## Current Inputs We Have

### Template

- Aries_Template.accdb

### Current Repo Aries Export Surface

- AriesExportService.cs
- AriesExportBundleService.cs
- ImportScopedAriesService.cs

### Prior Reference Logic

The last best Aries conversion behavior currently lives in:

- `internal source path`
- `internal source path`
- `internal source path`
- `internal source path`
- `internal source path`
- `internal source path`
- `internal source path`

## What The Current Repo Already Produces

The current `AriesExportBundleService` can already assemble:

### Reference datasets

- `MasterTableDefinition`
- `SidefileTable`
- `GroupsTable`
- `GroupListTable`
- `ScenarioTable`
- `SetupDataTable`
- `ProjectTable`
- `SortFiltersTable`
- `SelFiltersTable`

### Lease-scoped datasets

- `MasterTableRows`
- `EconTable`
- `ProductTable`
- `TestTable`

That means the Access writer should not invent a new export model. It should write these existing datasets into the Aries template.

## What The Aries Template Appears To Expect

String inspection of the template suggests the Access file contains or references names like:

- `Master`
- `Economic`
- `Product`
- `Test`
- `SideFile`
- `Project`
- `LOOKUP`
- `Setup Data Lines`
- `Economic Scenario Data`
- `Group P/Z Table`

These names are enough to establish a first target table map, but they should still be verified by opening the template in Access.

## First-Pass Mapping Target

This is the working initial table map for implementation.

| Current dataset | First Aries template target | Notes |
| --- | --- | --- |
| `MasterTableRows` | `Master` | Lease/property master rows |
| `EconTable` | `Economic` | Main economic input lines |
| `ProductTable` | `Product` | Monthly production rows |
| `TestTable` | `Test` | Test data rows |
| `SidefileTable` | `SideFile` | Resolved sidefile rows |
| `ProjectTable` | `Project` | Project-level lookup/reference rows |
| `GroupsTable` | `Groups` or template-specific group table | Verify exact template object name |
| `GroupListTable` | `GroupList` or template-specific group table | Verify exact template object name |
| `ScenarioTable` | `Economic Scenario Data` | Verify exact template object name |
| `SetupDataTable` | `Setup Data Lines` | Verify exact template object name |
| `SortFiltersTable` | `SortFilters` | May be helper/reference only |
| `SelFiltersTable` | `SelFilters` | May be helper/reference only |

## What Is Missing Today

The current import harness does **not** yet have enough import-scoped Aries logic to claim parity with `tauris-webapi`.

The missing behavior is mostly in resolved economic line generation:

- setup-line expansion
- common-line inclusion
- default-line merge behavior
- scenario-section resolution
- lookup expansion
- sidefile expansion
- macro substitution
- project-to-property expansion

Those behaviors are implemented in `tauris-webapi` and are centered in `AriesService.GetEconTable(...)` and its helpers.

## Implementation Constraint

The current import-scoped Aries surface is narrow:

- `ValidateLeaseAsync`
- `GetMasterTableAsync`

It does **not** yet expose import-scoped equivalents for:

- econ table generation
- sidefile resolution
- product/test rows
- setup/scenario/reference tables

That means the next implementation step is not simply "write the `.accdb`."

It is:

1. expand import-scoped Aries services so they can build the same datasets from staged import data
2. port the missing resolution behavior from `tauris-webapi`
3. then write those resolved datasets into the Aries template

## Recommended First Working Scope

Build `Aries Access DB` in two passes.

### Pass 1

Goal:

- prove the template writer works
- populate the easiest stable tables first

Tables:

- `Master`
- `Product`
- `Test`
- `Project`
- `Scenario`
- `Setup Data Lines`
- `SideFile`

Behavior:

- write a fresh copy of the uploaded Aries template
- drop/recreate the populated tables where needed
- write rows in batches
- keep the same Access file-size and `255`-column guardrails already used for PHDWin Access export

### Pass 2

Goal:

- port economic-line fidelity from `tauris-webapi`

Focus:

- `Economic`
- lookup expansion
- sidefile expansion
- setup common/default lines
- scenario section selection
- macro substitution

## Selection Model

For the first working pass, `Aries Access DB` should default to:

- all leases in `PHD_MAINLSE`

Later, if needed, the UI can grow:

- explicit lease selection
- project/filter/sort subset export
- no-sidefile toggles

## Conversion Scope Model

The resolved Aries layer should be designed for fast re-conversion of a subset, not full-database-only rebuilds.

### Why

When a conversion defect is found in one case, we should not need to:

- re-upload the source dataset
- re-extract Clarion tables
- restage the full raw database
- rebuild the full Aries resolved output

Instead, the workflow should be:

1. keep the raw PHDWin layer fixed for that import
2. re-run the resolved conversion only for the affected scope
3. re-export only that resolved scope when debugging

### Required scopes

The conversion layer should eventually support:

- `ConvertAll`
- `ConvertLease(leaseId)`
- `ConvertProject(projectName or projectKey)`
- `ConvertFilter(filterId)`
- `ConvertSort(sortId)`

For the first implementation pass, `ConvertAll` and `ConvertLease(leaseId)` are enough.

### Stable key

The primary debug/reconversion key should be:

- `LSE_ID`

That key already exists in the raw `PHD_MAINLSE` layer and should flow through the resolved Aries layer wherever possible.

### Recommended resolved-schema shape

The resolved Aries layer should be written so rows can be replaced by scope.

That means:

- each resolved table should carry the source `LSE_ID` when applicable
- helper/reference tables can remain full-dataset tables
- lease-scoped output tables should be delete-and-rebuild capable by `LSE_ID`

### Rebuild behavior

For `ConvertLease(leaseId)`:

1. delete prior resolved Aries rows for that `leaseId`
2. re-run conversion from the raw PHDWin staging layer
3. reinsert only the rebuilt resolved rows
4. leave all unrelated resolved rows untouched

That gives us fast debugging and safe iteration.

### Export behavior

Once scoped conversion exists, export should support:

- export whole resolved dataset
- export one lease
- later export project/filter/sort subsets

This is more important than background processing at this stage because it directly reduces iteration time during conversion debugging.

## Validation Expectations

Before calling the Aries Access export "working", verify:

1. the generated `.accdb` opens in Access
2. expected target tables exist
3. `Master`, `Economic`, `Product`, and `Test` have rows
4. saved queries in the template still open
5. wide-table truncation is logged when it occurs
6. optional compact/repair can be added after writes if the template proves sensitive

## Immediate Next Code Target

The next implementation pass should:

1. add a real `GenerateAriesAccessAsync(...)` branch in ImportExportService.cs
2. resolve the active Aries template through ImportTemplateService.cs
3. add import-scoped Aries dataset builders beyond `GetMasterTableAsync(...)`
4. port the missing economic resolution logic from `tauris-webapi`
