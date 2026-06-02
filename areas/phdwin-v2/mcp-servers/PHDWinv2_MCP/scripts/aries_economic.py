#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ECONOMIC_REQUIRED_TABLES = [
    "PHD_FORCAST",
]

ECONOMIC_RECOMMENDED_TABLES = [
    "PHD_PRODUCTNAMES",
    "PHD_LSESEGMENT",
    "PHD_LSEPRODVAL",
    "PHD_ECON",
    "PHD_INVEST",
    "PHD_INVESTDESCR",
    "PHD_CUMVOL",
    "MOD_SCEN",
    "MOD_TEMPLATE",
]

FORECAST_FIELD_CANDIDATES = [
    "LSE_ID",
    "ARCSEQ",
    "PRODUCTCODE",
    "START_DTTM",
    "STARTDATE",
    "START_DATE",
    "Q",
    "QI",
    "RATE",
    "DI",
    "DECLINE",
    "B",
    "EXPONENT",
    "D_MIN",
    "DMIN",
    "LIMIT",
    "ECONLIMIT",
]

ECON_FIELD_CANDIDATES = [
    "LSE_ID",
    "SEQ",
    "ECON_ID",
    "CASE_ID",
    "START_DTTM",
    "STARTDATE",
    "PRICE",
    "OILPRICE",
    "GASPRICE",
    "NGLPRICE",
    "DIFF",
    "SEV_TAX",
    "ADVAL_TAX",
    "OPCOST",
    "FIXED_COST",
    "VAR_COST",
    "LOE",
    "ESCALATION",
]

INVEST_FIELD_CANDIDATES = [
    "LSE_ID",
    "SEQ",
    "INV_ID",
    "INVEST_ID",
    "INVESTDESCR_ID",
    "DESCR_ID",
    "DATE_DTTM",
    "DATE",
    "AMOUNT",
    "COST",
    "CAPITAL",
    "TANGIBLE",
    "INTANGIBLE",
    "ABANDONMENT",
]

INVEST_DESCRIPTION_ID_FIELDS = [
    "INVESTDESCR_ID",
    "INVEST_DESCR_ID",
    "DESCR_ID",
    "DESCRIPTION_ID",
    "INV_ID",
    "INVEST_ID",
]

INVEST_DESCRIPTION_TEXT_FIELDS = [
    "DESCR",
    "DESCRIPTION",
    "NAME",
    "INVESTDESCR",
    "INVEST_DESCR",
    "LABEL",
]

SEGMENT_FIELD_CANDIDATES = [
    "LSE_ID",
    "SEG_ID",
    "SEGMENT_ID",
    "SEQ",
    "PRODUCTCODE",
    "START_DTTM",
    "STARTDATE",
    "END_DTTM",
    "ENDDATE",
    "RATE",
    "Q",
    "QI",
    "DI",
    "DECLINE",
    "B",
    "LIMIT",
]

PRODVAL_FIELD_CANDIDATES = [
    "LSE_ID",
    "SEQ",
    "PRODUCTCODE",
    "VALUE",
    "PRICE",
    "DIFF",
    "SHRINK",
    "YIELD",
    "BTU",
    "START_DTTM",
    "STARTDATE",
]

SCEN_FIELD_CANDIDATES = [
    "LSE_ID",
    "SCEN_ID",
    "SCENARIO_ID",
    "SCEN",
    "SCENARIO",
    "NAME",
    "DESCR",
    "DESCRIPTION",
    "SEQ",
    "START_DTTM",
    "STARTDATE",
]

TEMPLATE_FIELD_CANDIDATES = [
    "LSE_ID",
    "TPL_ID",
    "TEMPLATE_ID",
    "TEMPLATE",
    "NAME",
    "DESCR",
    "DESCRIPTION",
    "SEQ",
    "TYPE",
    "START_DTTM",
    "STARTDATE",
]

CUMVOL_FIELD_CANDIDATES = [
    "LSE_ID",
    "SEQ",
    "PRODUCTCODE",
    "OIL",
    "GAS",
    "WATER",
    "WTR",
    "NGL",
    "CUMOIL",
    "CUMGAS",
    "CUMWATER",
    "CUMWTR",
    "CUMNGL",
    "DATE_DTTM",
    "DATE",
]

PRODUCT_CODE_FIELDS = [
    "PRODUCTCODE",
    "PRODUCT_CODE",
    "PRODUCT",
]

PRODUCT_NAME_FIELDS = [
    "DESCR",
    "DESCRIPTION",
    "NAME",
    "PRODUCTNAME",
    "PRODUCT_NAME",
    "LABEL",
]


@dataclass
class AcEconomicBuildResult:
    rows: list[dict[str, Any]]
    warnings: list[str]
    diagnostics: dict[str, Any]


def _row_get(row: dict[str, Any], *names: str, default: Any = "") -> Any:
    by_upper = {str(k).upper(): v for k, v in row.items()}
    for name in names:
        if name.upper() in by_upper:
            value = by_upper[name.upper()]
            return default if value is None else value
    return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _lease_id(row: dict[str, Any]) -> int:
    return _to_int(_row_get(row, "LSE_ID", "LEASE_ID"))


def _filter_rows_by_lease(rows: list[dict[str, Any]], selected_lease_ids: set[int] | None) -> list[dict[str, Any]]:
    valid_rows = [row for row in rows if _lease_id(row) > 0]
    if selected_lease_ids is None:
        return valid_rows
    return [
        row
        for row in valid_rows
        if _lease_id(row) in selected_lease_ids
    ]


def _propnum_for_lease(lease_id: int) -> str:
    return f"PHD{lease_id:06d}"


def _clean_value(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).strip().split())


def _forecast_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        _lease_id(row),
        _to_int(_row_get(row, "ARCSEQ", "ARC_SEQ", "SEQ", "SEQUENCE")),
        _to_int(_row_get(row, "PRODUCTCODE", "PRODUCT_CODE", "PRODUCT")),
        _clean_value(_row_get(row, "START_DTTM", "STARTDATE", "START_DATE", default="")),
    )


def _forecast_expression(row: dict[str, Any]) -> str:
    return _source_expression(row, FORECAST_FIELD_CANDIDATES)


def _source_expression(row: dict[str, Any], candidates: list[str]) -> str:
    parts: list[str] = []
    by_upper = {str(key).upper(): value for key, value in row.items()}
    for field in candidates:
        if field in by_upper:
            parts.append(f"{field}={_clean_value(by_upper[field])}")
    if not parts:
        for key in sorted(row.keys(), key=str.upper):
            parts.append(f"{key}={_clean_value(row[key])}")
    return "; ".join(parts)


def _generic_source_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        _lease_id(row),
        _to_int(_row_get(row, "SEQ", "SEQUENCE")),
        _to_int(_row_get(row, "INV_ID", "INVEST_ID", "ECON_ID", "CASE_ID")),
        _clean_value(_row_get(row, "DATE_DTTM", "START_DTTM", "DATE", "STARTDATE", default="")),
    )


def _row_key(row: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        value = _clean_value(_row_get(row, field, default=""))
        if value:
            return value
    return ""


def _build_invest_description_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _row_key(row, INVEST_DESCRIPTION_ID_FIELDS)
        if key and key not in result:
            result[key] = row
    return result


def _description_text(row: dict[str, Any]) -> str:
    return _clean_value(_row_get(row, *INVEST_DESCRIPTION_TEXT_FIELDS, default=""))


def _product_code(row: dict[str, Any]) -> int:
    return _to_int(_row_get(row, *PRODUCT_CODE_FIELDS))


def _product_name(row: dict[str, Any]) -> str:
    return _clean_value(_row_get(row, *PRODUCT_NAME_FIELDS, default=""))


def _build_product_name_index(rows: list[dict[str, Any]]) -> dict[int, str]:
    result: dict[int, str] = {}
    for row in rows:
        code = _product_code(row)
        name = _product_name(row)
        if code > 0 and name and code not in result:
            result[code] = name
    return result


def _append_product_name(expression: str, row: dict[str, Any], product_names: dict[int, str]) -> tuple[str, bool]:
    code = _product_code(row)
    if code <= 0:
        return expression, False
    name = product_names.get(code)
    if not name:
        return expression, True
    return expression + f"; PRODUCT_NAME={name}", False


def _has_nonzero_forecast(row: dict[str, Any]) -> bool:
    """Return True when a forecast row has meaningful numeric data."""
    by_upper = {str(k).upper(): v for k, v in row.items()}
    segment_prefixes = ("Q_BEG$", "Q_END$", "DECLINE$", "N_FACTOR$", "SEGMENTDATE$", "DECLMIN$")
    scalar_fields = {"Q", "QI", "RATE", "DI", "DECLINE", "B", "EXPONENT"}
    for key, value in by_upper.items():
        if any(key.startswith(prefix) for prefix in segment_prefixes) or key in scalar_fields:
            if _to_float(value) != 0.0:
                return True
    return False


def _build_forecast_review_rows(
    forecast_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
    product_names: dict[int, str],
) -> tuple[list[dict[str, Any]], int]:
    scoped_rows = _filter_rows_by_lease(forecast_rows, selected_lease_ids)
    scoped_rows = [row for row in scoped_rows if _has_nonzero_forecast(row)]
    result: list[dict[str, Any]] = []
    unmatched_product_code_count = 0
    for sequence, row in enumerate(sorted(scoped_rows, key=_forecast_sort_key), start=1):
        lease_id = _lease_id(row)
        expression, unmatched_product = _append_product_name(_forecast_expression(row), row, product_names)
        if unmatched_product:
            unmatched_product_code_count += 1
        result.append(
            {
                "PROPNUM": _propnum_for_lease(lease_id),
                "SECTION": 1,
                "SEQUENCE": sequence,
                "QUALIFIER": "PY_REVIEW",
                "KEYWORD": "PY_REVIEW_FORECAST",
                "EXPRESSION": expression,
                "LINE": "PY_REVIEW_FORECAST " + expression,
                "SOURCE_TABLE": "PHD_FORCAST",
                "SOURCE_LSE_ID": lease_id,
                "SOURCE_ARCSEQ": _to_int(_row_get(row, "ARCSEQ", "ARC_SEQ", "SEQ", "SEQUENCE")),
                "SOURCE_PRODUCTCODE": _to_int(_row_get(row, "PRODUCTCODE", "PRODUCT_CODE", "PRODUCT")),
                "SOURCE_PRODUCT_NAME": product_names.get(_product_code(row), ""),
            }
        )
    return result, unmatched_product_code_count


def _build_source_review_rows(
    rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
    *,
    section: int,
    keyword: str,
    source_table: str,
    candidates: list[str],
    product_names: dict[int, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    scoped_rows = _filter_rows_by_lease(rows, selected_lease_ids)
    result: list[dict[str, Any]] = []
    unmatched_product_code_count = 0
    for sequence, row in enumerate(sorted(scoped_rows, key=_generic_source_sort_key), start=1):
        lease_id = _lease_id(row)
        expression = _source_expression(row, candidates)
        if product_names is not None:
            expression, unmatched_product = _append_product_name(expression, row, product_names)
            if unmatched_product:
                unmatched_product_code_count += 1
        result.append(
            {
                "PROPNUM": _propnum_for_lease(lease_id),
                "SECTION": section,
                "SEQUENCE": sequence,
                "QUALIFIER": "PY_REVIEW",
                "KEYWORD": keyword,
                "EXPRESSION": expression,
                "LINE": keyword + " " + expression,
                "SOURCE_TABLE": source_table,
                "SOURCE_LSE_ID": lease_id,
                "SOURCE_SEQ": _to_int(_row_get(row, "SEQ", "SEQUENCE")),
                "SOURCE_PRODUCTCODE": _product_code(row),
                "SOURCE_PRODUCT_NAME": product_names.get(_product_code(row), "") if product_names is not None else "",
            }
        )
    return result, unmatched_product_code_count


def _build_invest_review_rows(
    rows: list[dict[str, Any]],
    descriptions: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
) -> tuple[list[dict[str, Any]], int]:
    description_by_id = _build_invest_description_index(descriptions)
    scoped_rows = _filter_rows_by_lease(rows, selected_lease_ids)
    result: list[dict[str, Any]] = []
    unmatched_description_count = 0
    for sequence, row in enumerate(sorted(scoped_rows, key=_generic_source_sort_key), start=1):
        lease_id = _lease_id(row)
        expression = _source_expression(row, INVEST_FIELD_CANDIDATES)
        description_key = _row_key(row, INVEST_DESCRIPTION_ID_FIELDS)
        description = description_by_id.get(description_key) if description_key else None
        description_label = _description_text(description) if description else ""
        if description_key and not description:
            unmatched_description_count += 1
        if description_label:
            expression = expression + f"; INVEST_DESCRIPTION={description_label}"
        result.append(
            {
                "PROPNUM": _propnum_for_lease(lease_id),
                "SECTION": 3,
                "SEQUENCE": sequence,
                "QUALIFIER": "PY_REVIEW",
                "KEYWORD": "PY_REVIEW_INVEST",
                "EXPRESSION": expression,
                "LINE": "PY_REVIEW_INVEST " + expression,
                "SOURCE_TABLE": "PHD_INVEST",
                "SOURCE_LSE_ID": lease_id,
                "SOURCE_SEQ": _to_int(_row_get(row, "SEQ", "SEQUENCE")),
                "SOURCE_INVESTDESCR_ID": description_key,
                "SOURCE_INVEST_DESCRIPTION": description_label,
            }
        )
    return result, unmatched_description_count


def build_ac_economic_rows(
    source_tables: dict[str, list[dict[str, Any]]],
    selected_lease_ids: set[int] | None = None,
) -> AcEconomicBuildResult:
    """Build AC_ECONOMIC rows from PHDWin source tables.

    This is currently a diagnostics scaffold. It centralizes the economics
    entry point so deep-fidelity generation can be added behind tests without
    burying the logic in aries_export.py.
    """
    normalized = {name.upper(): rows for name, rows in source_tables.items()}
    table_counts = {
        table: len(normalized.get(table, []))
        for table in ECONOMIC_REQUIRED_TABLES + ECONOMIC_RECOMMENDED_TABLES
    }
    missing_required = [
        table
        for table in ECONOMIC_REQUIRED_TABLES
        if table_counts.get(table, 0) == 0
    ]
    missing_recommended = [
        table
        for table in ECONOMIC_RECOMMENDED_TABLES
        if table_counts.get(table, 0) == 0
    ]

    scoped_counts = {
        table: len(_filter_rows_by_lease(normalized.get(table, []), selected_lease_ids))
        for table in table_counts
    }
    missing_lease_id_counts = {
        table: sum(1 for row in normalized.get(table, []) if _lease_id(row) <= 0)
        for table in table_counts
    }

    product_names = _build_product_name_index(normalized.get("PHD_PRODUCTNAMES", []))
    unmatched_product_code_counts: dict[str, int] = {}

    forecast_rows, unmatched_product_code_counts["PHD_FORCAST"] = _build_forecast_review_rows(
        normalized.get("PHD_FORCAST", []),
        selected_lease_ids,
        product_names,
    )
    econ_rows, _ = _build_source_review_rows(
        normalized.get("PHD_ECON", []),
        selected_lease_ids,
        section=2,
        keyword="PY_REVIEW_ECON",
        source_table="PHD_ECON",
        candidates=ECON_FIELD_CANDIDATES,
    )
    invest_rows, unmatched_invest_description_count = _build_invest_review_rows(
        normalized.get("PHD_INVEST", []),
        normalized.get("PHD_INVESTDESCR", []),
        selected_lease_ids,
    )
    segment_rows, unmatched_product_code_counts["PHD_LSESEGMENT"] = _build_source_review_rows(
        normalized.get("PHD_LSESEGMENT", []),
        selected_lease_ids,
        section=4,
        keyword="PY_REVIEW_SEGMENT",
        source_table="PHD_LSESEGMENT",
        candidates=SEGMENT_FIELD_CANDIDATES,
        product_names=product_names,
    )
    prodval_rows, unmatched_product_code_counts["PHD_LSEPRODVAL"] = _build_source_review_rows(
        normalized.get("PHD_LSEPRODVAL", []),
        selected_lease_ids,
        section=5,
        keyword="PY_REVIEW_PRODVAL",
        source_table="PHD_LSEPRODVAL",
        candidates=PRODVAL_FIELD_CANDIDATES,
        product_names=product_names,
    )
    scen_rows, _ = _build_source_review_rows(
        normalized.get("MOD_SCEN", []),
        selected_lease_ids,
        section=6,
        keyword="PY_REVIEW_SCEN",
        source_table="MOD_SCEN",
        candidates=SCEN_FIELD_CANDIDATES,
    )
    template_rows, _ = _build_source_review_rows(
        normalized.get("MOD_TEMPLATE", []),
        selected_lease_ids,
        section=7,
        keyword="PY_REVIEW_TEMPLATE",
        source_table="MOD_TEMPLATE",
        candidates=TEMPLATE_FIELD_CANDIDATES,
    )
    cumvol_rows, unmatched_product_code_counts["PHD_CUMVOL"] = _build_source_review_rows(
        normalized.get("PHD_CUMVOL", []),
        selected_lease_ids,
        section=8,
        keyword="PY_REVIEW_CUMVOL",
        source_table="PHD_CUMVOL",
        candidates=CUMVOL_FIELD_CANDIDATES,
        product_names=product_names,
    )
    rows = forecast_rows + econ_rows + invest_rows + segment_rows + prodval_rows + scen_rows + template_rows + cumvol_rows

    warnings: list[str] = []
    if missing_required:
        warnings.append(
            "AC_ECONOMIC deep-fidelity generation is blocked; missing required economic source tables: "
            + ", ".join(missing_required)
            + "."
        )
    if missing_recommended:
        warnings.append(
            "AC_ECONOMIC deep-fidelity generation is incomplete; missing recommended economic source tables: "
            + ", ".join(missing_recommended)
            + "."
        )
    missing_lease_tables = [
        f"{table}={count}"
        for table, count in missing_lease_id_counts.items()
        if count
    ]
    if missing_lease_tables:
        warnings.append(
            "Economic source rows without usable LSE_ID were skipped: "
            + ", ".join(missing_lease_tables)
            + "."
        )
    unmatched_product_tables = [
        f"{table}={count}"
        for table, count in unmatched_product_code_counts.items()
        if count
    ]
    if unmatched_product_tables:
        warnings.append(
            "Economic source rows with product codes missing from PHD_PRODUCTNAMES: "
            + ", ".join(unmatched_product_tables)
            + "."
        )
    if rows:
        warnings.append(
            "AC_ECONOMIC contains Python review rows only. "
            "Rows are deterministic coverage artifacts, not verified final Aries economic syntax."
        )
    if unmatched_invest_description_count:
        warnings.append(
            "PHD_INVEST rows with description identifiers had no matching PHD_INVESTDESCR row: "
            + str(unmatched_invest_description_count)
            + "."
        )
    else:
        warnings.append(
            "AC_ECONOMIC deep-fidelity row generation is not implemented yet in the Python MCP exporter; "
            "economic source tables were inventoried for review only."
        )

    return AcEconomicBuildResult(
        rows=rows,
        warnings=warnings,
        diagnostics={
            "tableCounts": table_counts,
            "scopedTableCounts": scoped_counts,
            "missingLeaseIdCounts": missing_lease_id_counts,
            "unmatchedProductCodeCounts": unmatched_product_code_counts,
            "productNameCount": len(product_names),
            "missingRequiredTables": missing_required,
            "missingRecommendedTables": missing_recommended,
            "selectedLeaseIds": sorted(selected_lease_ids) if selected_lease_ids else None,
            "forecastReviewRowCount": len(forecast_rows),
            "econReviewRowCount": len(econ_rows),
            "investReviewRowCount": len(invest_rows),
            "segmentReviewRowCount": len(segment_rows),
            "prodvalReviewRowCount": len(prodval_rows),
            "scenarioReviewRowCount": len(scen_rows),
            "templateReviewRowCount": len(template_rows),
            "cumvolReviewRowCount": len(cumvol_rows),
            "reviewRowCount": len(rows),
            "unmatchedInvestDescriptionCount": unmatched_invest_description_count,
            "status": "source_review_rows" if rows else "diagnostics_only",
        },
    )
