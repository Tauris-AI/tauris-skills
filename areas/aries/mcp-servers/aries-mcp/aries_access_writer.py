#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


DateParser = Callable[[Any], date | None]


DEFAULT_EXPORT_TABLE_ORDER = [
    "AC_PROPERTY",
    "AC_PRODUCT",
    "AC_TEST",
    "AC_DAILY",
    "AC_ECONOMIC",
    "ARLOOKUP",
    "AR_SIDEFILE",
    "AC_OWNER",
    "GROUPTEST",
    "AC_SCENARIO",
    "AC_SETUPDATA",
    "PROJECT",
    "PROJLIST",
    "SORTFILTERS",
    "SelFilters",
]
DEFAULT_STALE_DATA_TABLES = [
    "AC_DETAIL",
    "AC_ECOSUM",
    "AC_FCST",
    "AC_MONTHLY",
    "AC_NOTE",
    "AC_ONELINE",
    "AC_PZFCST",
    "AC_RATIO",
    "AC_RESERVES",
    "AC_WELL",
    "GROUPLIST",
    "GROUPS",
]
DEFAULT_REPLACE_TABLES = {
    *DEFAULT_EXPORT_TABLE_ORDER,
    *DEFAULT_STALE_DATA_TABLES,
}


@dataclass
class AriesTableWriteSummary:
    table: str
    before_count: int | None = None
    inserted_count: int = 0
    after_count: int | None = None
    matched_columns: list[str] = field(default_factory=list)
    unmatched_columns: list[str] = field(default_factory=list)
    added_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class AriesAccessWriteSummary:
    accdb_path: str
    tables: dict[str, AriesTableWriteSummary] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    integrity: dict[str, Any] = field(default_factory=dict)
    status: str = "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "accdbPath": self.accdb_path,
            "status": self.status,
            "warnings": self.warnings,
            "tables": {
                name: {
                    "beforeCount": table.before_count,
                    "insertedCount": table.inserted_count,
                    "afterCount": table.after_count,
                    "matchedColumns": table.matched_columns,
                    "unmatchedColumns": table.unmatched_columns,
                    "addedColumns": table.added_columns,
                    "warnings": table.warnings,
                }
                for name, table in self.tables.items()
            },
            "integrity": self.integrity,
        }


class AriesAccessWriterError(RuntimeError):
    def __init__(self, message: str, summary: AriesAccessWriteSummary | None = None):
        super().__init__(message)
        self.summary = summary


def _clean_name(value: Any) -> str:
    return str(value).replace("\x00", "")


def q(identifier: str) -> str:
    return "[" + identifier.replace("]", "]]") + "]"


def clean_text(value: Any, max_len: int | None = None) -> str:
    text = "" if value is None else str(value).strip()
    text = " ".join(text.split())
    if max_len is not None:
        return text[:max_len]
    return text


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value))
    except (TypeError, ValueError):
        return default


def clarion_date_to_date(value: Any) -> date | None:
    serial = to_int(value, default=-1)
    if serial < 0:
        return None
    return date(1800, 12, 28) + timedelta(days=serial)


def parse_access_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            pass
    return clarion_date_to_date(value)


def row_get(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    by_upper = {str(k).upper(): v for k, v in row.items()}
    for name in names:
        if name.upper() in by_upper:
            value = by_upper[name.upper()]
            return default if value is None else value
    return default


class AriesAccessWriter:
    def __init__(
        self,
        accdb_path: Path,
        *,
        dbskey: str,
        column_aliases: dict[str, dict[str, tuple[str, ...]]] | None = None,
        schema_extensions: dict[str, list[dict[str, str]]] | None = None,
        date_parser: DateParser = parse_access_date,
    ) -> None:
        self.accdb_path = accdb_path
        self.dbskey = dbskey
        self.column_aliases = column_aliases or {}
        self.schema_extensions = schema_extensions or {}
        self.date_parser = date_parser
        self.pyodbc: Any | None = None
        self.conn: Any | None = None
        self.cursor: Any | None = None
        self.summary = AriesAccessWriteSummary(accdb_path=str(accdb_path))

    @classmethod
    def from_template(
        cls,
        template_path: Path,
        output_path: Path,
        **kwargs: Any,
    ) -> "AriesAccessWriter":
        if not template_path.exists():
            raise FileNotFoundError(f"Missing Aries Access template: {template_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template_path, output_path)
        return cls(output_path, **kwargs)

    def __enter__(self) -> "AriesAccessWriter":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.conn is None:
            return
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()
        self.conn = None
        self.cursor = None

    def connect(self) -> None:
        try:
            import pyodbc  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pyodbc is required for .accdb export. CSV export does not require pyodbc.") from exc
        self.pyodbc = pyodbc
        conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};Dbq={self.accdb_path};Pooling=false"
        self.conn = pyodbc.connect(conn_str, autocommit=False)
        self.conn.setdecoding(pyodbc.SQL_CHAR, encoding="latin-1")
        self.conn.setdecoding(pyodbc.SQL_WCHAR, encoding="latin-1")
        self.conn.setdecoding(pyodbc.SQL_WMETADATA, encoding="utf-16-le")
        self.conn.setencoding(encoding="utf-8")
        self.cursor = self.conn.cursor()

    def _require_cursor(self) -> Any:
        if self.cursor is None:
            raise RuntimeError("AriesAccessWriter is not connected.")
        return self.cursor

    def table_names(self) -> set[str]:
        cursor = self._require_cursor()
        names = set()
        for row in cursor.tables(tableType="TABLE"):
            try:
                names.add(_clean_name(row.table_name).upper())
            except AttributeError:
                names.add(_clean_name(row[2]).upper())
        return names

    def table_count(self, table_name: str) -> int:
        cursor = self._require_cursor()
        return int(cursor.execute(f"SELECT COUNT(*) FROM {q(table_name)}").fetchone()[0])

    def columns_from_description(self, table_name: str) -> list[str]:
        cursor = self._require_cursor()
        cursor.execute(f"SELECT * FROM {q(table_name)} WHERE 1=0")
        return [_clean_name(column[0]) for column in cursor.description]

    def column_schema(self, table_name: str) -> dict[str, dict[str, Any]]:
        cursor = self._require_cursor()
        schema: dict[str, dict[str, Any]] = {}
        for row in cursor.columns(table=table_name):
            column_name = _clean_name(row.column_name)
            schema[column_name.upper()] = {
                "name": column_name,
                "data_type": int(row.data_type),
                "type_name": _clean_name(row.type_name).upper(),
                "column_size": int(row.column_size or 0),
                "nullable": int(row.nullable) if row.nullable is not None else 1,
            }
        return schema

    def ensure_columns(self, table_name: str, specs: list[dict[str, str]]) -> list[str]:
        cursor = self._require_cursor()
        columns = self.columns_from_description(table_name)
        existing = {column.upper() for column in columns}
        summary = self.summary.tables.setdefault(table_name, AriesTableWriteSummary(table=table_name))
        for spec in specs:
            column_name = spec["name"]
            if column_name.upper() in existing:
                continue
            cursor.execute(f"ALTER TABLE {q(table_name)} ADD COLUMN {q(column_name)} {spec['accdb_type']}")
            summary.added_columns.append(column_name)
            existing.add(column_name.upper())
        return self.columns_from_description(table_name)

    def clear_table(self, table_name: str) -> None:
        cursor = self._require_cursor()
        summary = self.summary.tables.setdefault(table_name, AriesTableWriteSummary(table=table_name))
        summary.before_count = self.table_count(table_name)
        cursor.execute(f"DELETE FROM {q(table_name)}")
        summary.after_count = self.table_count(table_name)

    def _row_value(self, row: dict[str, Any], table_name: str, column: str) -> Any:
        value = row_get(row, column, default=None)
        if value not in {None, ""}:
            return value
        for alias in self.column_aliases.get(table_name.upper(), {}).get(column.upper(), ()):
            value = row_get(row, alias, default=None)
            if value not in {None, ""}:
                return value
        return value

    def _coerce_value(self, value: Any, schema: dict[str, Any]) -> Any:
        if value is None or value == "":
            return None

        data_type = int(schema.get("data_type", 0))
        type_name = str(schema.get("type_name", "")).upper()

        if data_type in {91, 92, 93} or "DATE" in type_name or "TIME" in type_name:
            parsed = self.date_parser(value)
            return datetime.combine(parsed, datetime.min.time()) if parsed else None

        if data_type in {-6, 2, 3, 4, 5} or type_name in {"BYTE", "SHORT", "INTEGER", "LONG"}:
            return to_int(value)

        if data_type in {6, 7, 8} or type_name in {"SINGLE", "DOUBLE", "DECIMAL", "NUMERIC", "CURRENCY"}:
            return to_float(value)

        text = clean_text(value)
        column_size = int(schema.get("column_size", 0))
        if column_size > 0 and column_size < 100000 and len(text) > column_size:
            return text[:column_size]
        return text

    def write_table(self, table_name: str, rows: list[dict[str, Any]], scope_key: str | None = None) -> None:
        cursor = self._require_cursor()
        summary = self.summary.tables.setdefault(table_name, AriesTableWriteSummary(table=table_name))
        summary.before_count = self.table_count(table_name)
        columns = self.columns_from_description(table_name)
        columns = self.ensure_columns(table_name, self.schema_extensions.get(table_name.upper(), []))
        schema_by_upper = self.column_schema(table_name)
        columns_by_upper = {column.upper(): column for column in columns}

        # Fresh-template exports must be idempotent and must not retain sample
        # project/property rows from a populated ARIES template. AC_SETUPDATA is
        # additive: preserve template setup rows and only replace generated
        # sections with the same SECNAME values.
        if table_name.upper() == "AC_SETUPDATA" and rows:
            secnames = sorted({
                clean_text(row_get(row, "SECNAME"))
                for row in rows
                if clean_text(row_get(row, "SECNAME"))
            })
            if secnames and "SECNAME" in columns_by_upper:
                placeholders = ", ".join("?" for _ in secnames)
                cursor.execute(f"DELETE FROM {q(table_name)} WHERE {q(columns_by_upper['SECNAME'])} IN ({placeholders})", secnames)
        else:
            cursor.execute(f"DELETE FROM {q(table_name)}")

        if rows:
            row_keys = {key for row in rows for key in row.keys()}
            row_keys_upper = {key.upper() for key in row_keys}
            alias_targets = {
                target
                for target, aliases in self.column_aliases.get(table_name.upper(), {}).items()
                if target.upper() in columns_by_upper
                and any(alias.upper() in row_keys_upper for alias in aliases)
            }
            insert_columns = [
                columns_by_upper[column.upper()]
                for column in sorted(row_keys | alias_targets, key=str.upper)
                if column.upper() in columns_by_upper
            ]
            summary.matched_columns = insert_columns
            summary.unmatched_columns = sorted(
                [key for key in row_keys if key.upper() not in columns_by_upper],
                key=str.upper,
            )
            required_missing = [
                spec["name"]
                for key, spec in schema_by_upper.items()
                if int(spec.get("nullable", 1)) == 0
                and spec["name"] not in insert_columns
                and key not in {"COUNTER", "ID"}
            ]
            if required_missing:
                raise AriesAccessWriterError(
                    f"Required Access columns missing for {table_name}: {required_missing}",
                    self.summary,
                )
            if not insert_columns:
                raise AriesAccessWriterError(
                    f"No matching Access columns for {table_name}; row keys={sorted(row_keys, key=str.upper)}",
                    self.summary,
                )
            placeholders = ", ".join("?" for _ in insert_columns)
            sql = f"INSERT INTO {q(table_name)} ({', '.join(q(column) for column in insert_columns)}) VALUES ({placeholders})"
            values = [
                [
                    self._coerce_value(self._row_value(row, table_name, column), schema_by_upper[column.upper()])
                    for column in insert_columns
                ]
                for row in rows
            ]
            cursor.fast_executemany = False
            cursor.executemany(sql, values)
            summary.inserted_count = len(rows)
        summary.after_count = self.table_count(table_name)
        if table_name.upper() == "AC_SETUPDATA":
            return
        if summary.after_count != len(rows):
            raise AriesAccessWriterError(
                f"{table_name} final row count {summary.after_count} does not match build count {len(rows)}.",
                self.summary,
            )

    def append_showids_column(self, column_name: str) -> None:
        if "DBSLIST" not in self.table_names():
            return
        columns = {column.upper() for column in self.columns_from_description("DBSLIST")}
        if "DBSKEY" not in columns or "SHOWIDS" not in columns:
            self.summary.warnings.append("DBSLIST exists but is missing DBSKEY or SHOWIDS; SRC_DB display governance skipped.")
            return
        cursor = self._require_cursor()
        row = cursor.execute(f"SELECT {q('SHOWIDS')} FROM {q('DBSLIST')} WHERE {q('DBSKEY')} = ?", self.dbskey).fetchone()
        if row is None:
            self.summary.warnings.append(f"DBSLIST row for DBSKEY {self.dbskey} was not found; SRC_DB was not appended to SHOWIDS.")
            return
        existing = "" if row[0] is None else str(row[0])
        tokens = [token.strip() for token in existing.split(",") if token.strip()]
        if any(token.upper() == column_name.upper() for token in tokens):
            return
        updated = ", ".join([*tokens, column_name]) if tokens else column_name
        cursor.execute(
            f"UPDATE {q('DBSLIST')} SET {q('SHOWIDS')} = ? WHERE {q('DBSKEY')} = ?",
            updated,
            self.dbskey,
        )

    def _table_rows(self, table_name: str, columns: list[str]) -> list[dict[str, Any]]:
        cursor = self._require_cursor()
        select_sql = ", ".join(q(column) for column in columns)
        rows = cursor.execute(f"SELECT {select_sql} FROM {q(table_name)}").fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def _propnum_set(self) -> set[str]:
        if "AC_PROPERTY" not in self.table_names():
            return set()
        return {
            str(row["PROPNUM"])
            for row in self._table_rows("AC_PROPERTY", ["PROPNUM"])
            if row.get("PROPNUM") not in {None, ""}
        }

    def _extract_propnum(self, value: Any) -> str:
        text = "" if value is None else str(value)
        match = re.search(r"PROPNUM\s*=\s*'([^']+)'", text, re.IGNORECASE)
        return match.group(1) if match else text

    def assert_integrity(self) -> None:
        available = self.table_names()
        propnums = self._propnum_set()
        integrity: dict[str, Any] = {"orphanCounts": {}, "scenarioQualifierOrphans": []}

        checks = {
            "AC_ECONOMIC": "PROPNUM",
            "AC_PRODUCT": "PROPNUM",
            "AC_TEST": "PROPNUM",
            "AC_DAILY": "PROPNUM",
            "AC_OWNER": "PROPNUM",
        }
        for table_name, column_name in checks.items():
            if table_name not in available:
                continue
            rows = self._table_rows(table_name, [column_name])
            orphans = sorted({
                str(row[column_name])
                for row in rows
                if row.get(column_name) not in {None, ""} and str(row[column_name]) not in propnums
            })
            integrity["orphanCounts"][table_name] = len(orphans)
            if orphans:
                integrity[f"{table_name}Orphans"] = orphans[:25]

        if "PROJLIST" in available:
            rows = self._table_rows("PROJLIST", ["PROPKEY"])
            orphans = sorted({
                self._extract_propnum(row["PROPKEY"])
                for row in rows
                if row.get("PROPKEY") not in {None, ""}
                and self._extract_propnum(row["PROPKEY"]) not in propnums
            })
            integrity["orphanCounts"]["PROJLIST"] = len(orphans)
            if orphans:
                integrity["PROJLISTOrphans"] = orphans[:25]

        if "AC_ECONOMIC" in available and "AC_SCENARIO" in available:
            econ_rows = self._table_rows("AC_ECONOMIC", ["SECTION", "QUALIFIER"])
            scenario_columns = self.columns_from_description("AC_SCENARIO")
            qualifier_columns = [column for column in scenario_columns if column.upper().startswith("QUAL")]
            scenario_selectors: set[tuple[int, str]] = set()
            scenario_select_columns = ["DATA_SECT", *qualifier_columns]
            for row in self._table_rows("AC_SCENARIO", scenario_select_columns):
                section = to_int(row.get("DATA_SECT"))
                for column in qualifier_columns:
                    qualifier = clean_text(row.get(column))
                    if qualifier:
                        scenario_selectors.add((section, qualifier))
            missing = sorted({
                (to_int(row.get("SECTION")), clean_text(row.get("QUALIFIER")))
                for row in econ_rows
                if clean_text(row.get("QUALIFIER"))
                and (to_int(row.get("SECTION")), clean_text(row.get("QUALIFIER"))) not in scenario_selectors
            })
            integrity["scenarioQualifierOrphans"] = [
                {"section": section, "qualifier": qualifier}
                for section, qualifier in missing
            ]

        self.summary.integrity = integrity
        failed = any(count for count in integrity["orphanCounts"].values()) or bool(integrity["scenarioQualifierOrphans"])
        if failed:
            self.summary.status = "fail"
            raise AriesAccessWriterError("ARIES Access post-write integrity checks failed.", self.summary)


def write_access_database(
    tables: dict[str, list[dict[str, Any]]],
    template_path: Path,
    output_path: Path,
    *,
    dbskey: str,
    table_order: list[str] | None = None,
    stale_data_tables: list[str] | None = None,
    schema_extensions: dict[str, list[dict[str, str]]] | None = None,
    column_aliases: dict[str, dict[str, tuple[str, ...]]] | None = None,
    date_parser: DateParser = parse_access_date,
) -> AriesAccessWriteSummary:
    table_order = table_order or DEFAULT_EXPORT_TABLE_ORDER
    stale_data_tables = stale_data_tables or DEFAULT_STALE_DATA_TABLES
    writer = AriesAccessWriter.from_template(
        template_path,
        output_path,
        dbskey=dbskey,
        column_aliases=column_aliases,
        schema_extensions=schema_extensions,
        date_parser=date_parser,
    )
    with writer:
        available_tables = writer.table_names()
        for table_name in stale_data_tables:
            if table_name.upper() in available_tables:
                writer.clear_table(table_name)
        for table_name in table_order:
            if table_name.upper() not in available_tables:
                writer.summary.warnings.append(f"Access table {table_name} not found in template; skipped.")
                continue
            writer.write_table(table_name, tables.get(table_name, []))
        writer.append_showids_column("SRC_DB")
        writer.assert_integrity()
    return writer.summary
