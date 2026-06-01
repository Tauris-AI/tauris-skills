# Aries Codebase Inventory

## Purpose

This document records where Aries conversion functionality already lives inside the current `Tauris.PhdWin` repo.

The key conclusion is:

- we do **not** need to copy the whole Aries conversion stack from `tauris-webapi`
- a large portion of the conversion engine is already present in this repo
- the remaining work is mainly integration into the import-scoped staged workflow

## Current Repo Aries Areas

### `Tauris.PhdWin.Server`

Current in-repo PHDWin-specific Aries conversion and export work:

- AriesExportService.cs
- AriesExportBundleService.cs
- ImportScopedAriesService.cs
- ImportAriesResolvedService.cs

These currently provide:

- resolved `Master`
- resolved `Product`
- resolved `Test`
- scoped conversion by job / lease
- first Aries Access export for:
  - `AC_PROPERTY`
  - `AC_PRODUCT`
  - `AC_TEST`

### `Tauris.Aries.Common`

This repo already contains a broader Aries conversion library under:

- `internal source path`

Important existing files there:

- IAriesService.cs
- SubstitutionService.cs
- ScenarioRepository.cs
- LookupRepository.cs
- SidefileRepository.cs
- EconRepository.cs
- ProjlistRepository.cs
- ProjectRepository.cs
- LookupExpressionEntity.cs
- MacroNotFoundException.cs

These already implement major portions of the deeper Aries econ flow:

- scenario section selection
- lookup expansion
- sidefile expansion
- macro substitution
- econ-table orchestration

## What `tauris-webapi` Is Still Useful For

`tauris-webapi` is still useful as:

- a comparison source
- a reference for more recent variants of the orchestration
- a place to cross-check any drift between implementations

It should **not** be treated as the long-term home for the functionality we are building here.

## What Still Needs To Be Integrated In This Repo

Even though much of the code already exists here, it is not yet fully adapted to the new import-scoped workflow.

Main remaining integration tasks:

1. adapt the broader Aries econ orchestration to staged import jobs
2. decide where to reuse `Tauris.Aries.Common` directly vs where to build import-scoped adapters
3. integrate the resulting resolved econ output into:
   - resolved Postgres layer
   - `AC_ECON`
   - Aries project/group/incremental output

## Immediate Working Conclusion

The next implementation phase is:

- not bulk code copying
- but integration and adaptation inside this repo

The code ownership now looks like:

- current repo = source of truth
- `tauris-webapi` = reference only
