# Aries Conversion Next Steps

## Current Position

The current repo now owns the core ingestion path:

- upload
- normalize
- extract
- raw staged workspace data
- raw PostgreSQL staging when enabled
- first resolved Aries conversion layer

Current resolved Aries conversion already supports:

- `Master`
- `Product`
- `Test`

Current scope support already exists for:

- `ConvertAll`
- `ConvertLease(leaseId)`

Current limitation:

- `Aries Access DB` is not yet a real writer
- `AC_ECON` is not yet ported into the import-scoped conversion workflow

Important repo ownership note:

- much of the deeper Aries orchestration is already present in this repo under `src/Tauris.Aries.Common`
- see:
  - ARIES_CODEBASE_INVENTORY.md

## Immediate Goal

Create the first real `Aries Access DB` export from this repo.

First export target tables:

- `AC_PROPERTY`
- `AC_PRODUCT`
- `AC_TEST`

These should be populated from the resolved Aries layer that already exists in this repo.

## Working Rules

1. Keep all ingestion, extraction, conversion, and export logic in this repo.
2. Use `tauris-webapi` only as a reference source for porting logic.
3. Keep the Aries template intact for now.
4. Do not rely on manual template edits as the primary implementation path.
5. Prefer scoped reconversion by `LSE_ID` when debugging.

## Confirmed Template Direction

The Aries template indicates that `Master` maps to:

- `AC_PROPERTY`

The template appears to expect a minimal property-oriented shape, not the current broad resolved master row.

Confirmed baseline fields that must exist in every generated `AC_PROPERTY` row:

- `DBSKEY`
- `PROPNUM`
- `SEQ`
- `MAJOR`
- `PRIOR_OIL`
- `PRIOR_GAS`
- `PRIOR_WTR`

Primary key expectation:

- `DBSKEY + PROPNUM`

## Immediate Implementation Cadence

### Phase 1

Build the first real Aries Access writer for:

- `AC_PROPERTY`
- `AC_PRODUCT`
- `AC_TEST`

Tasks:

1. Copy the active Aries template to a new output `.accdb`
2. Drop and recreate `AC_PROPERTY`
3. Populate `AC_PROPERTY` from the resolved `aries_master` layer
4. Drop and recreate `AC_PRODUCT`
5. Populate `AC_PRODUCT` from the resolved `aries_product` layer
6. Drop and recreate `AC_TEST`
7. Populate `AC_TEST` from the resolved `aries_test` layer
8. Package the populated `.accdb` into the export ZIP

### Phase 2

Integrate the import-scoped Aries econ resolver using the code already present in this repo, with `tauris-webapi` used only for comparison/fill-in.

Required orchestration pieces:

- setup/default line logic
- scenario section resolution
- sidefile expansion
- lookup expansion
- macro substitution

Result:

- resolved `AC_ECON`-ready output in this repo

### Phase 3

Add project/group/incremental population into the resolved/export path.

Includes:

- Aries project creation
- groups
- group list
- incrementals

### Phase 4

Validate Arps/equation conversion behavior and tighten edge cases.

## First Coding Session Scope

When work begins, the first coding session should aim to complete:

1. `Aries Access DB` writer scaffold
2. `AC_PROPERTY` create/populate path
3. `AC_PRODUCT` create/populate path
4. `AC_TEST` create/populate path

That is the fastest path to a first usable Aries database artifact from this repo.

## What The User Should Expect First

The first working Aries database export will likely include:

- property/master data
- monthly production data
- test data

It will not yet include the full final econ conversion until the next porting pass is completed.

## Start Command For The Next Session

When the user says to begin, commence with:

1. Aries Access writer implementation
2. minimal `AC_PROPERTY` contract enforcement
3. `AC_PRODUCT` and `AC_TEST` population
4. one Windows-side export validation run
