# Aries Schema Mapping

Updated: 2026-05-12

This document is the working schema and relationship map for Aries Access reference databases used by the PHDWin import harness.

Current primary reference database:

- an external sanitized Aries Access template supplied outside the Cowork plugin package

Secondary reference material:

- ARIES_ACCESS_TABLE_CONTRACTS.md
- ARIES_EXPORT_RUNNING_LIST.md
- PHDWIN_DATA_MAP.md

## Working Model

Current working interpretation:

- `PROJECT` defines a project-level Aries economic object
- `PROJLIST` defines the members of that project
- `AC_PROPERTY.PROPNUM` is the critical property/case anchor
- `SelFilters` and `SORTFILTERS` are project-scoped behavior tables
- `GROUPS` in PHDWin are being used as incrementals
- those incrementals represent economic difference entities built from multiple cases
- `GROUPLIST` is therefore best treated as the source-side membership table for the incremental/group entity
- `GROUPTEST` is intentionally out of scope for the current pass

Current relationship chain to validate:

1. source PHDWin `PHD_GROUPS`
2. source PHDWin `PHD_GROUPLIST`-style membership source
3. Aries `PROJECT`
4. Aries `PROJLIST`
5. Aries `AC_PROPERTY`
6. Aries `SelFilters`
7. Aries `SORTFILTERS`

## Project Types

The current working project model now has three project types:

### 1. Default dataset project

Purpose:

- one default Aries project representing the whole imported dataset

Working name:

- `00_RSV_CAT`

Working intent:

- this acts as the default `All Cases` view in Aries
- the Aries key remains `00_RSV_CAT`, but the user-facing default project should read as `All Cases`

### 2. Partner projects

Purpose:

- one Aries project per partner or qualified ownership context

Primary source candidates:

- `PHD_OWNER`
- `PHD_MAINLSE`
- later Aries-side ownership output in `AC_OWNER`

Working interpretation:

- partner projects are ownership-driven and are not the same thing as the PHD group/incremental objects
- each partner project should carry its own qualified ownership line behavior in Aries

### 3. Incremental / group projects

Purpose:

- Aries projects representing economic difference entities

Primary source candidates:

- `PHD_GROUPS`
- `PHD_LIST`

Working interpretation:

- these groups are economic entities that take the difference of multiple cases
- the source-side member list lives in `PHD_LIST`

## Priority Order

The current mapping priority is:

1. `PROJECT`
2. `PROJLIST`
3. `AC_PROPERTY`
4. `SelFilters`
5. `SORTFILTERS`
6. `GROUP` / `GROUPLIST` source-side interpretation
7. `AC_SCENARIO`
8. `AC_SETUPDATA`

## Table Notes

### `PROJECT`

Purpose:

- defines the Aries project/incremental object

What we need to confirm:

- practical key shape
- relationship to `PROJLIST`
- whether one `DBSKEY` can own many projects
- whether project rows differ between simple case projects and incremental/group projects

Current evidence:

- multiple projects exist in the internal reference database used to derive this mapping
- this makes it the preferred reference over the earlier single-project database

### `PROJLIST`

Purpose:

- bridges project membership to individual Aries properties/cases

Why it matters:

- this is the most important relationship table in the current pass
- it is the bridge between project identity and `AC_PROPERTY.PROPNUM`

What we need to confirm:

- whether `PROPKEY` or `INTKEY` is the effective property member key
- how `PROJSEQ` ordering behaves
- whether `SCENARIO` is a true scenario selector or just carried descriptive context
- how incrementals/groups are represented relative to ordinary property members

Current source-side note:

- the source-side membership analog appears to be split:
  - explicit project membership through `PHD_LIST`
  - ownership semantics through `PHD_OWNER`

Current implementation direction:

- prefer `PHD_LIST` as the primary project-membership source when it exists
- use `PHD_OWNER` `SEQ = 1` only as a fallback membership source
- treat ownership rows as the qualified-interest layer, not the primary member list

### `AC_PROPERTY`

Purpose:

- property/case master table

Critical point:

- `PROPNUM` is currently the most important join target in the whole mapping effort

What we need to confirm:

- exact `PROPNUM` shape for ordinary cases, incrementals, platforms, and any synthetic Aries entities
- how `DBSKEY + PROPNUM` appears in related expression-driven tables

Observed examples already recovered from reference strings:

- `DBSKEY='168888' AND PROPNUM='PHD00344'`
- `DBSKEY='168888' AND PROPNUM='INCR00344'`
- non-`168888` project keys also appear in the newer multi-project database

### `SelFilters`

Purpose:

- project-level selection/filter behavior

Working interpretation:

- rows are keyed by project and sequence
- they define filtering behavior over the member property universe represented through `PROJLIST` and `AC_PROPERTY`

Current confirmed examples from screenshots:

- `TAI_EXCLUDE is Null`
- `RSV_CAT is one of PDP, PUD, PROB`
- `LSE_ID is one of 2.00`

Important notes:

- `PROPNUM` is not necessarily stored directly in `SelFilters`
- but the meaning of each filter row depends on the project membership defined by `PROJLIST`
- current export direction is to generate starter Aries filters from explicit project membership, not from any presumed active PHD UI filter state

### `SORTFILTERS`

Purpose:

- project-level sort stack behavior

Working interpretation:

- rows are keyed by project and sequence
- they describe how project members are ordered/grouped for Aries output

Current confirmed examples from screenshots:

- `FIELD`
- `RSV_CLASS`
- `RSV_CAT`
- `RSC_SORT`
- `LSE_ID`

Important notes:

- sort stacks vary by project
- the critical relationship is still project membership, not the sort rows by themselves
- current export direction is to generate a stable Aries starter sort stack rather than infer a last-used PHDWin sort

### `GROUP` / `GROUPLIST`

Current working interpretation:

- the user’s current business interpretation should be treated as primary
- `GROUPS` are being used as incrementals
- those incrementals take the economic difference of two or more cases
- `GROUPLIST` is the member list for that economic entity

Why this matters:

- this likely explains how certain Aries project rows and member rows are assembled
- it also explains why incremental-style `PROPNUM` values such as `INCR...` appear in the reference database

Current concrete source evidence from internal staging runs:

- `PHD_GROUPS` can contain named economic groups in addition to the default all-cases group
- `PHD_LIST` contains explicit `GRP_ID + LSE_ID` membership rows
- some groups include visible `{incr}` member cases
- different named groups may share visible lease membership while differing by ownership or other economic context

Implication:

- these source groups should be treated as intentional economic entities, not just UI folders

### `PHD_OWNER`

Purpose:

- source-side ownership and qualified interest definition

Why it matters now:

- partner projects are likely ownership-driven
- this table is now first-class in the mapping effort

Current evidence from internal staging runs:

- group `1` (`All Cases`) has:
  - `1426` `SEQ = 1` ownership rows
  - `5` `SEQ = 2` rows
  - `5` `SEQ = 3` rows
- groups `2` through `5` currently show only `SEQ = 1`

Working interpretation:

- `SEQ = 1` appears to represent the primary/default ownership line for a case within a project/group context
- higher-sequence rows likely represent additional qualified ownership/reversion behavior and should eventually feed Aries ownership output

## Out Of Scope For This Pass

Do not spend current mapping effort on:

- `GROUPTEST`

Reason:

- the immediate problem is project membership and project behavior mapping
- `GROUPTEST` can be documented later if it becomes necessary for export correctness

## Immediate Next Steps

1. Recover exact `PROJECT`, `PROJLIST`, `SelFilters`, and `SORTFILTERS` table definitions from the Aries reference template or a user-provided Aries database.
2. Recover representative rows for several distinct projects from a user-provided Aries database.
3. Match those projects to `PROJLIST` members and then back to `AC_PROPERTY.PROPNUM`.
4. Compare that Aries-side relationship graph to:
   - ownership-driven partner membership from `PHD_OWNER`
   - incremental/group membership from `PHD_GROUPS` and `PHD_LIST`
5. Only after that, adjust `ImportScopedAriesService` to match the reference behavior.
