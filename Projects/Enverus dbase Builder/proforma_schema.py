#!/usr/bin/env python3
r"""
proforma_schema.py -- SINGLE SOURCE OF TRUTH for AC_PROPERTY column iteration.

This is the one file to edit when you want to add, amend, or remove an
AC_PROPERTY column. Three scripts read this spec, so a change here flows through
the whole pipeline in one edit:

    build_project.py   -> writes the column (+ value) into proforma_AC_PROPERTY.csv
    load_proforma.py   -> ALTERs the SQLite AC_PROPERTY (if missing) + populates it
    make_accdb.py      -> ALTERs the Access AC_PROPERTY (if missing) + inserts it

Column naming follows the governed convention: ALL-CAPS, underscores, <=12 chars,
no "crazy characters". New columns should also be registered in DBSLIST.SHOWIDS
for the governing DBSKEY so ARIES displays them (governance step -- see
CODEX_HANDOFF.md).

Each entry:
    name        column name (governed convention above)
    after       insert immediately after this existing column (CSV ordering)
    value       constant written to every row; None => computed at runtime
    sqlite_type DDL type if the column must be created in SQLite
    accdb_type  DDL type if the column must be created in Access
"""
from __future__ import annotations

import glob
import os
import re


EXTRA_PROPERTY_COLS = [
    {
        "name": "RSV_CAT",
        "after": "PROPNUM",
        "value": "01PDP",
        "sqlite_type": "TEXT",
        "accdb_type": "VARCHAR(12)",
    },
    {
        "name": "SRC_DB",
        "after": "RSV_CAT",
        "value": None,
        "sqlite_type": "TEXT",
        "accdb_type": "VARCHAR(255)",
    },
]


def friendly_name(*paths: str) -> str:
    """ARIES-safe friendly name from source filename(s).

    Takes the common stem across the basenames, strips a trailing ISO date, and
    replaces any run of non-alphanumerics with a single underscore. For example:
    env_csv-Production-badec_2026-06-04.csv + env_csv-Wells-e8117_2026-06-04.csv
    -> "env_csv".
    """
    stems = [
        re.sub(
            r"[-_]\d{4}-\d{2}-\d{2}$",
            "",
            os.path.splitext(os.path.basename(path))[0],
        )
        for path in paths
    ]
    stems = [stem for stem in stems if stem]
    if not stems:
        return "SOURCE"
    name = os.path.commonprefix(stems) if len(stems) > 1 else stems[0]
    name = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")
    return name or "SOURCE"


def source_db_name(ext_dir: str) -> str:
    """Friendly source-db name derived from the source CSVs in ext_dir."""
    files = sorted(glob.glob(os.path.join(ext_dir, "*.csv")))
    return friendly_name(*files)


def resolved_extra_cols(ext_dir: str) -> list[dict]:
    """EXTRA_PROPERTY_COLS with runtime-computed values filled in."""
    resolved = []
    for column in EXTRA_PROPERTY_COLS:
        column = dict(column)
        if column["name"] == "SRC_DB" and column["value"] is None:
            column["value"] = source_db_name(ext_dir)
        resolved.append(column)
    return resolved


def order_columns(base_cols: list[str], extras: list[dict]) -> list[str]:
    """Insert each extra column immediately after its 'after' anchor.

    Columns already present in base_cols are left in place and not duplicated.
    Extras whose anchor is missing are appended at the end.
    """
    columns = list(base_cols)
    for column in extras:
        if column["name"] in columns:
            continue
        if column["after"] in columns:
            columns.insert(columns.index(column["after"]) + 1, column["name"])
        else:
            columns.append(column["name"])
    return columns
