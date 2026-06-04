#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


def sqlite_type(access_type: str | None) -> str:
    normalized = (access_type or "").upper()
    if any(token in normalized for token in ["INT", "LONG", "SHORT", "BYTE", "BIT", "YESNO"]):
        return "INTEGER"
    if any(token in normalized for token in ["DOUBLE", "FLOAT", "REAL", "NUMERIC", "DECIMAL", "CURRENCY"]):
        return "REAL"
    if any(token in normalized for token in ["DATE", "TIME"]):
        return "TEXT"
    if any(token in normalized for token in ["BINARY", "IMAGE", "OLE"]):
        return "BLOB"
    return "TEXT"


def quote_access_identifier(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def quote_sqlite_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def clean_column_names(raw_names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    cleaned: list[str] = []
    for index, raw_name in enumerate(raw_names, start=1):
        name = str(raw_name or f"column_{index}").strip() or f"column_{index}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        cleaned.append(name if count == 0 else f"{name}_{count + 1}")
    return cleaned


def normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def access_objects(cursor: Any, table_type: str) -> list[str]:
    objects: list[str] = []
    for row in cursor.tables(tableType=table_type):
        table_name = str(getattr(row, "table_name", row[2]))
        if table_name and not table_name.upper().startswith("MSYS"):
            objects.append(table_name)
    return sorted(set(objects), key=str.upper)


def access_tables(cursor: Any) -> list[str]:
    return access_objects(cursor, "TABLE")


def access_views(cursor: Any) -> list[str]:
    return access_objects(cursor, "VIEW")


def access_columns(cursor: Any, table_name: str) -> list[tuple[str, str]]:
    columns: list[tuple[str, str]] = []
    try:
        for row in cursor.columns(table=table_name):
            column_name = str(getattr(row, "column_name", row[3]))
            type_name = str(getattr(row, "type_name", "") or "")
            columns.append((column_name, sqlite_type(type_name)))
    except UnicodeDecodeError:
        return []
    return columns


def export_access_to_sqlite(access_path: Path, sqlite_path: Path, driver: str) -> None:
    try:
        import pyodbc
    except ImportError as exc:
        raise SystemExit("pyodbc is required to convert Access templates") from exc

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        sqlite_path.unlink()

    conn_str = f"DRIVER={{{driver}}};DBQ={access_path};READONLY=TRUE;"
    source = pyodbc.connect(conn_str, autocommit=True)
    target = sqlite3.connect(sqlite_path)
    try:
        source_cursor = source.cursor()
        target_cursor = target.cursor()
        target_cursor.execute(
            """
            CREATE TABLE TEMPLATE_METADATA (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            )
            """
        )
        target_cursor.executemany(
            "INSERT INTO TEMPLATE_METADATA(key, value) VALUES (?, ?)",
            [
                ("template_type", "aries_access_sqlite"),
                ("source_file", access_path.name),
                ("generated_by", "scripts/build_reference_sqlite_templates.py"),
                ("generated_on", date.today().isoformat()),
                ("scope", "SQLite copy of the bundled Access template for local review/testing"),
                ("view_export", "Access views are materialized into __access_view_* backing tables and exposed as SQLite views"),
            ],
        )

        for table_name in access_tables(source_cursor):
            export_access_selectable(
                source_cursor,
                target_cursor,
                source_name=table_name,
                sqlite_table_name=table_name,
                column_defs=access_columns(source_cursor, table_name),
            )

        for view_name in access_views(source_cursor):
            backing_table_name = f"__access_view_{re.sub(r'[^A-Za-z0-9_]', '_', view_name)}"
            column_names = export_access_selectable(
                source_cursor,
                target_cursor,
                source_name=view_name,
                sqlite_table_name=backing_table_name,
                column_defs=[],
            )
            select_columns = ", ".join(quote_sqlite_identifier(name) for name in column_names)
            target_cursor.execute(
                f"CREATE VIEW {quote_sqlite_identifier(view_name)} AS "
                f"SELECT {select_columns} FROM {quote_sqlite_identifier(backing_table_name)}"
            )

        target.commit()
    finally:
        source.close()
        target.close()


def export_access_selectable(
    source_cursor: Any,
    target_cursor: sqlite3.Cursor,
    source_name: str,
    sqlite_table_name: str,
    column_defs: list[tuple[str, str]],
) -> list[str]:
    source_cursor.execute(f"SELECT * FROM {quote_access_identifier(source_name)}")
    fetched_column_names = clean_column_names([column[0] for column in source_cursor.description])
    type_by_column = {name: col_type for name, col_type in column_defs}
    create_columns = ", ".join(
        f"{quote_sqlite_identifier(name)} {type_by_column.get(name, 'TEXT')}"
        for name in fetched_column_names
    )
    target_cursor.execute(
        f"CREATE TABLE {quote_sqlite_identifier(sqlite_table_name)} ({create_columns})"
    )
    rows = source_cursor.fetchall()
    if rows:
        placeholders = ", ".join("?" for _ in fetched_column_names)
        target_cursor.executemany(
            f"INSERT INTO {quote_sqlite_identifier(sqlite_table_name)} VALUES ({placeholders})",
            [[normalize_value(value) for value in row] for row in rows],
        )
    return fetched_column_names


def safe_table_name(name: str) -> str:
    if not re.fullmatch(r"[A-Z0-9_]+", name):
        raise ValueError(f"Unexpected table name: {name}")
    return name


def create_table(conn: sqlite3.Connection, table_name: str, columns: list[str]) -> None:
    safe_name = safe_table_name(table_name)
    column_sql = ", ".join(f"{quote_sqlite_identifier(column)} TEXT" for column in columns)
    conn.execute(f"CREATE TABLE {quote_sqlite_identifier(safe_name)} ({column_sql})")


def insert_rows(conn: sqlite3.Connection, table_name: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    safe_name = safe_table_name(table_name)
    placeholders = ", ".join("?" for _ in columns)
    conn.executemany(
        f"INSERT INTO {quote_sqlite_identifier(safe_name)} VALUES ({placeholders})",
        [[row.get(column) for column in columns] for row in rows],
    )


def generate_phdwin_template(sqlite_path: Path) -> None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        sqlite_path.unlink()

    tables: dict[str, tuple[list[str], list[dict[str, Any]]]] = {
        "TEMPLATE_METADATA": (
            ["key", "value"],
            [
                {"key": "template_type", "value": "phdwin_review_sqlite"},
                {"key": "generated_by", "value": "scripts/build_reference_sqlite_templates.py"},
                {"key": "generated_on", "value": date.today().isoformat()},
                {"key": "scope", "value": "Synthetic one-lease PHDWin review fixture with 76 PHD/MOD source tables; no client data"},
                {"key": "source_table_count", "value": "76"},
                {"key": "sanitization", "value": "All identifiers, names, locations, dates, volumes, and economics are fabricated"},
            ],
        ),
        "PHD_TITLES": (
            ["PROJECT_ID", "PROJECT_NAME", "CASE_SET", "EFFECTIVE_DATE", "NOTES"],
            [
                {
                    "PROJECT_ID": "TPL_PROJECT",
                    "PROJECT_NAME": "SANITIZED TEMPLATE PROJECT",
                    "CASE_SET": "BASE",
                    "EFFECTIVE_DATE": "2026-01-01",
                    "NOTES": "Synthetic template row for agent testing only",
                }
            ],
        ),
        "PHD_MAINLSE": (
            [
                "LSE_ID",
                "LSE_NAME",
                "API",
                "OPERATOR",
                "FIELD",
                "COUNTY",
                "STATE",
                "RESERVE_CLASS",
                "RESERVE_CATEGORY",
                "GRP_ID",
                "FIRST_PROD_DATE",
            ],
            [
                {
                    "LSE_ID": "TPL_LSE_0001",
                    "LSE_NAME": "SANITIZED LEASE 0001",
                    "API": "00-000-00000",
                    "OPERATOR": "REDACTED OPERATOR",
                    "FIELD": "REDACTED FIELD",
                    "COUNTY": "REDACTED COUNTY",
                    "STATE": "XX",
                    "RESERVE_CLASS": "PDP",
                    "RESERVE_CATEGORY": "PROVED",
                    "GRP_ID": "TPL_GRP_01",
                    "FIRST_PROD_DATE": "2025-01-01",
                }
            ],
        ),
        "PHD_GROUPS": (
            ["GRP_ID", "GROUP_NAME", "DESCRIPTION"],
            [{"GRP_ID": "TPL_GRP_01", "GROUP_NAME": "SANITIZED GROUP", "DESCRIPTION": "Synthetic ownership/project group"}],
        ),
        "PHD_LIST": (
            ["LIST_ID", "GRP_ID", "LSE_ID", "SORT_ORDER"],
            [{"LIST_ID": "TPL_LIST_01", "GRP_ID": "TPL_GRP_01", "LSE_ID": "TPL_LSE_0001", "SORT_ORDER": "1"}],
        ),
        "PHD_OWNER": (
            ["LSE_ID", "GRP_ID", "SEQ", "OWNER_NAME", "WORKING_INTEREST", "NET_REVENUE_INTEREST", "BURDEN"],
            [
                {
                    "LSE_ID": "TPL_LSE_0001",
                    "GRP_ID": "TPL_GRP_01",
                    "SEQ": "1",
                    "OWNER_NAME": "REDACTED OWNER",
                    "WORKING_INTEREST": "1.000000",
                    "NET_REVENUE_INTEREST": "0.800000",
                    "BURDEN": "0.200000",
                }
            ],
        ),
        "PHD_ADJOWNER": (
            ["LSE_ID", "GRP_ID", "SEQ", "ADJUSTMENT_TYPE", "ADJUSTMENT_VALUE"],
            [{"LSE_ID": "TPL_LSE_0001", "GRP_ID": "TPL_GRP_01", "SEQ": "1", "ADJUSTMENT_TYPE": "NONE", "ADJUSTMENT_VALUE": "0"}],
        ),
        "PHD_PRODUCTNAMES": (
            ["PRODUCTCODE", "PRODUCT_NAME", "UNIT"],
            [
                {"PRODUCTCODE": "OIL", "PRODUCT_NAME": "Oil", "UNIT": "BBL"},
                {"PRODUCTCODE": "GAS", "PRODUCT_NAME": "Gas", "UNIT": "MCF"},
                {"PRODUCTCODE": "NGL", "PRODUCT_NAME": "NGL", "UNIT": "BBL"},
            ],
        ),
        "PHD_FORCAST": (
            ["LSE_ID", "ARCSEQ", "PRODUCTCODE", "START_DATE", "QI", "DI", "B_FACTOR", "MIN_DECLINE", "ECON_LIMIT"],
            [
                {"LSE_ID": "TPL_LSE_0001", "ARCSEQ": "1", "PRODUCTCODE": "OIL", "START_DATE": "2026-01-01", "QI": "100.0", "DI": "0.6500", "B_FACTOR": "0.9000", "MIN_DECLINE": "0.0600", "ECON_LIMIT": "1.0"},
                {"LSE_ID": "TPL_LSE_0001", "ARCSEQ": "1", "PRODUCTCODE": "GAS", "START_DATE": "2026-01-01", "QI": "600.0", "DI": "0.6200", "B_FACTOR": "0.8500", "MIN_DECLINE": "0.0600", "ECON_LIMIT": "10.0"},
            ],
        ),
        "PHD_MONHIST": (
            ["LSE_ID", "TYPE", "YEAR", "MONTH", "PRODUCTCODE", "VOLUME", "DAYS_ON"],
            [
                {"LSE_ID": "TPL_LSE_0001", "TYPE": "M", "YEAR": "2025", "MONTH": "1", "PRODUCTCODE": "OIL", "VOLUME": "3000.0", "DAYS_ON": "31"},
                {"LSE_ID": "TPL_LSE_0001", "TYPE": "M", "YEAR": "2025", "MONTH": "1", "PRODUCTCODE": "GAS", "VOLUME": "18000.0", "DAYS_ON": "31"},
            ],
        ),
        "PHD_CUMVOL": (
            ["LSE_ID", "PRODUCTCODE", "CUM_VOLUME", "AS_OF_DATE"],
            [
                {"LSE_ID": "TPL_LSE_0001", "PRODUCTCODE": "OIL", "CUM_VOLUME": "3000.0", "AS_OF_DATE": "2025-01-31"},
                {"LSE_ID": "TPL_LSE_0001", "PRODUCTCODE": "GAS", "CUM_VOLUME": "18000.0", "AS_OF_DATE": "2025-01-31"},
            ],
        ),
        "PHD_LSEPRODVAL": (
            ["LSE_ID", "PRODUCTCODE", "PRICE", "DIFFERENTIAL", "SHRINK_YIELD"],
            [
                {"LSE_ID": "TPL_LSE_0001", "PRODUCTCODE": "OIL", "PRICE": "70.00", "DIFFERENTIAL": "-2.50", "SHRINK_YIELD": "1.0000"},
                {"LSE_ID": "TPL_LSE_0001", "PRODUCTCODE": "GAS", "PRICE": "3.50", "DIFFERENTIAL": "-0.25", "SHRINK_YIELD": "1.0000"},
            ],
        ),
        "PHD_LSESEGMENT": (
            ["LSE_ID", "SEGMENT_ID", "SEGMENT_TYPE", "START_DATE", "VALUE", "NOTES"],
            [{"LSE_ID": "TPL_LSE_0001", "SEGMENT_ID": "TPL_SEG_01", "SEGMENT_TYPE": "BASE_DECLINE", "START_DATE": "2026-01-01", "VALUE": "1", "NOTES": "Synthetic base segment"}],
        ),
        "PHD_ECON": (
            ["LSE_ID", "EFFECTIVE_DATE", "LOE_FIXED", "LOE_VARIABLE", "SEV_TAX_RATE", "AD_VAL_TAX_RATE"],
            [{"LSE_ID": "TPL_LSE_0001", "EFFECTIVE_DATE": "2026-01-01", "LOE_FIXED": "2500.00", "LOE_VARIABLE": "1.25", "SEV_TAX_RATE": "0.0460", "AD_VAL_TAX_RATE": "0.0150"}],
        ),
        "PHD_INVEST": (
            ["LSE_ID", "INVEST_ID", "INVEST_DATE", "AMOUNT", "CATEGORY"],
            [{"LSE_ID": "TPL_LSE_0001", "INVEST_ID": "TPL_CAPEX_01", "INVEST_DATE": "2026-01-01", "AMOUNT": "100000.00", "CATEGORY": "FUTURE_CAPITAL"}],
        ),
        "PHD_INVESTDESCR": (
            ["INVEST_ID", "DESCRIPTION"],
            [{"INVEST_ID": "TPL_CAPEX_01", "DESCRIPTION": "Synthetic future capital"}],
        ),
        "MOD_SCEN": (
            ["SCEN_ID", "SCENARIO_NAME", "PRICE_SET", "COST_SET"],
            [{"SCEN_ID": "TPL_SCEN_01", "SCENARIO_NAME": "SANITIZED BASE CASE", "PRICE_SET": "TPL_PRICE", "COST_SET": "TPL_COST"}],
        ),
        "MOD_TEMPLATE": (
            ["TEMPLATE_ID", "TEMPLATE_NAME", "DESCRIPTION"],
            [{"TEMPLATE_ID": "TPL_MODEL_01", "TEMPLATE_NAME": "SANITIZED MODEL TEMPLATE", "DESCRIPTION": "Synthetic model assumptions"}],
        ),
        "PHD_FILTER": (
            ["FLT_ID", "FILTER_NAME", "DESCRIPTION"],
            [{"FLT_ID": "TPL_FILTER_01", "FILTER_NAME": "ALL SANITIZED LEASES", "DESCRIPTION": "Synthetic filter"}],
        ),
        "PHD_FILTERLINE": (
            ["FLT_ID", "SEQ", "FIELD_NAME", "OPERATOR", "VALUE"],
            [{"FLT_ID": "TPL_FILTER_01", "SEQ": "1", "FIELD_NAME": "GRP_ID", "OPERATOR": "=", "VALUE": "TPL_GRP_01"}],
        ),
        "PHD_SORT": (
            ["SRT_ID", "SORT_NAME", "FIELD_NAME", "DIRECTION"],
            [{"SRT_ID": "TPL_SORT_01", "SORT_NAME": "LEASE NAME", "FIELD_NAME": "LSE_NAME", "DIRECTION": "ASC"}],
        ),
        "PHD_CLASS": (
            ["CLASS_CODE", "CLASS_NAME"],
            [{"CLASS_CODE": "PDP", "CLASS_NAME": "Proved Developed Producing"}],
        ),
        "PHD_CATEGORY": (
            ["CATEGORY_CODE", "CATEGORY_NAME"],
            [{"CATEGORY_CODE": "PROVED", "CATEGORY_NAME": "Proved"}],
        ),
        "PHD_IDLABELS": (
            ["LABEL_ID", "LABEL_NAME"],
            [
                {"LABEL_ID": "FIELD", "LABEL_NAME": "Field"},
                {"LABEL_ID": "OPERATOR", "LABEL_NAME": "Operator"},
            ],
        ),
        "PHD_IDCODES": (
            ["LABEL_ID", "CODE", "DESCRIPTION"],
            [
                {"LABEL_ID": "FIELD", "CODE": "REDACTED_FIELD", "DESCRIPTION": "Sanitized field code"},
                {"LABEL_ID": "OPERATOR", "CODE": "REDACTED_OPERATOR", "DESCRIPTION": "Sanitized operator code"},
            ],
        ),
    }

    broad_source_tables = [
        "PHD_TITLES",
        "PHD_MAINLSE",
        "PHD_PRODUCTNAMES",
        "PHD_OWNER",
        "PHD_GROUPS",
        "PHD_LIST",
        "PHD_ADJOWNER",
        "PHD_FILTER",
        "PHD_FILTERLINE",
        "PHD_SORT",
        "PHD_CLASS",
        "PHD_CATEGORY",
        "PHD_IDCODES",
        "PHD_IDLABELS",
        "PHD_FORCAST",
        "PHD_LSEPRODVAL",
        "PHD_LSESEGMENT",
        "PHD_MONHIST",
        "PHD_CUMVOL",
        "PHD_INVEST",
        "PHD_INVESTDESCR",
        "PHD_ECON",
        "PHD_ALLOCDAT",
        "PHD_ARCHIVE",
        "PHD_BASEUNITS",
        "PHD_COMMENT",
        "PHD_CONVENTIONS",
        "PHD_CONVENTIONUNITS",
        "PHD_CONVERSIONS",
        "PHD_DAILY",
        "PHD_ECOCHANGE",
        "PHD_ENERGYADJ",
        "PHD_FLUIDS",
        "PHD_FORCECHANGECAT",
        "PHD_GCA",
        "PHD_GCALINE",
        "PHD_GRAPHS",
        "PHD_GRAVITY",
        "PHD_LOGIN",
        "PHD_MSCINFO",
        "PHD_ORDER",
        "PHD_PHDCASECHANGE",
        "PHD_PHDWINEMAIL",
        "PHD_PHDWINUSER",
        "PHD_RISK",
        "PHD_ROYALTY",
        "PHD_ROYALTYADJ",
        "PHD_RPTGRP",
        "PHD_RPTLSE",
        "PHD_RPTSCRLN",
        "PHD_RPTSCRPT",
        "PHD_UNITS",
        "PHD_VERSION",
        "PHD_VOLUME",
        "PHD_ZONE",
        "MOD_CANPRICE",
        "MOD_CURRENCY",
        "MOD_CURRENCYRATE",
        "MOD_DEPRCHILD",
        "MOD_DEPRECIATION",
        "MOD_DEPRMODELS",
        "MOD_DEPRTYPE",
        "MOD_DEPRVALUES",
        "MOD_KEY",
        "MOD_MODID",
        "MOD_MODPRODVAL",
        "MOD_MODSEGMENT",
        "MOD_MODVER",
        "MOD_SCEN",
        "MOD_TEMPLATE",
        "MOD_TIMESTAMP",
        "MOD_TPLIDCODE",
        "MOD_TPLPRODSEGMENT",
        "MOD_TPLPRODUCT",
        "MOD_USER",
        "MOD_VERSION",
    ]

    placeholder_columns = [
        "LSE_ID",
        "GRP_ID",
        "SEQ",
        "SOURCE_ROLE",
        "SANITIZED_VALUE",
        "NOTES",
    ]
    for table_name in broad_source_tables:
        if table_name in tables:
            continue
        tables[table_name] = (
            placeholder_columns,
            [
                {
                    "LSE_ID": "TPL_LSE_0001",
                    "GRP_ID": "TPL_GRP_01",
                    "SEQ": "1",
                    "SOURCE_ROLE": "placeholder_schema",
                    "SANITIZED_VALUE": "SYNTHETIC",
                    "NOTES": "Synthetic placeholder row; replace with real exported columns when a native PHDWin dataset is available",
                }
            ],
        )

    source_table_count = sum(1 for table_name in tables if table_name.startswith(("PHD_", "MOD_")))
    if source_table_count != 76:
        raise RuntimeError(f"Expected 76 synthetic PHD/MOD tables, found {source_table_count}")

    conn = sqlite3.connect(sqlite_path)
    try:
        for table_name, (columns, rows) in tables.items():
            create_table(conn, table_name, columns)
            insert_rows(conn, table_name, columns, rows)
        conn.commit()
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build scrubbed SQLite reference templates.")
    parser.add_argument("--access-template", type=Path)
    parser.add_argument("--aries-sqlite", type=Path)
    parser.add_argument("--phdwin-sqlite", type=Path)
    parser.add_argument("--access-driver", default="Microsoft Access Driver (*.mdb, *.accdb)")
    parser.add_argument("--skip-access", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.phdwin_sqlite:
        generate_phdwin_template(args.phdwin_sqlite)
        print(f"Wrote PHDWin SQLite template: {args.phdwin_sqlite}")
    if not args.skip_access:
        if not args.access_template or not args.aries_sqlite:
            raise SystemExit("--access-template and --aries-sqlite are required unless --skip-access is set")
        export_access_to_sqlite(args.access_template, args.aries_sqlite, args.access_driver)
        print(f"Wrote ARIES SQLite template: {args.aries_sqlite}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
