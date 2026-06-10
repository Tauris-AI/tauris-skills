#!/usr/bin/env python3
from __future__ import annotations

import math
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

ECONOMIC_STATUS_EMPTY = "empty"
ECONOMIC_STATUS_REVIEW_ROWS_ONLY = "review_rows_only"
ECONOMIC_STATUS_FINAL_ROWS_PRESENT = "final_rows_present"
ECONOMIC_STATUS_MIXED_REVIEW_AND_FINAL = "mixed_review_and_final"
REVIEW_QUALIFIER = "PY_REVIEW"

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

# ─── ARIES keyword and unit mappings ─────────────────────────────────────────

PRODUCT_ARIES_KEYWORD: dict[int, str] = {
    1: "GAS",
    2: "OIL",
    3: "WTR",
    4: "NGL",
    5: "CND",
}

PRODUCT_RATE_UNIT: dict[int, str] = {
    1: "M/M",    # Gas: Mcf/month
    2: "B/M",    # Oil: bbl/month
    3: "B/M",    # Water: bbl/month
    4: "B/M",    # NGL: bbl/month
    5: "B/M",    # Condensate: bbl/month
}

PRODUCT_PRICE_UNIT: dict[int, str] = {
    1: "$/M",    # Gas: $/Mcf
    2: "$/B",    # Oil: $/bbl
    3: "$/B",    # Water: $/bbl
    4: "$/B",    # NGL: $/bbl
    5: "$/B",    # Condensate: $/bbl
}

INVEST_KEYWORD_MAP: dict[str, str] = {
    "DRILLING": "DRILL",
    "DRILL": "DRILL",
    "COMPLETION": "COMPL",
    "COMPL": "COMPL",
    "WORKOVER": "WRKOVR",
    "WRKOVR": "WRKOVR",
    "ABANDONMENT": "CAPITAL",
    "ABANDON": "CAPITAL",
}

DEFAULT_INVEST_KEYWORD = "CAPITAL"


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
                "QUALIFIER": REVIEW_QUALIFIER,
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
                "QUALIFIER": REVIEW_QUALIFIER,
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
                "QUALIFIER": REVIEW_QUALIFIER,
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


# ─── Decline convention conversion ───────────────────────────────────────────

def _nominal_to_effective_annual(di_nominal: float, b: float = 0.0) -> float:
    """Convert nominal annual decline rate to effective annual decline.

    For exponential (b=0): D_eff = 1 - exp(-Di_nom)
    For hyperbolic (b>0): D_eff = 1 - (1 + b * Di_nom)^(-1/b)
    """
    if di_nominal <= 0:
        return 0.0
    if b <= 0:
        return 1.0 - math.exp(-di_nominal)
    return 1.0 - (1.0 + b * di_nominal) ** (-1.0 / b)


def _format_decline_pct(value: float) -> str:
    """Format effective annual decline as a percentage value for ARIES expressions."""
    if value <= 0:
        return "0"
    return f"{value * 100:.6f}"


# ─── Final ARIES row builders ────────────────────────────────────────────────
#
# Each builder follows the section-by-section map in:
#   references/ac-economic-builder-guide.md
#   references/ac-economic-line-grammar.md
#   references/ac-economic-keyword-catalog.md
#
# Expression formats are the verified Tauris patterns from the grammar reference.
# Decline values are converted to effective annual per ac-economic-calculations.md.


def _build_final_title_rows(
    lease_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
) -> list[dict[str, Any]]:
    """Generate Section 1 TITLES rows from PHD_MAINLSE.

    Builder guide §1: ``TITLES <lease id>, <lease name>``
    Keep unqualified; section 1 is not scenario-selected.
    """
    scoped = _filter_rows_by_lease(lease_rows, selected_lease_ids)
    result: list[dict[str, Any]] = []

    for row in sorted(scoped, key=lambda r: _lease_id(r)):
        lease_id = _lease_id(row)
        propnum = _propnum_for_lease(lease_id)
        lse_name = _clean_value(_row_get(row, "LSE_NAME", "LEASE_NAME", "NAME", default=""))

        expression = f"{propnum}, {lse_name}" if lse_name else propnum
        result.append({
            "PROPNUM": propnum, "SECTION": 1, "SEQUENCE": 0,
            "QUALIFIER": "", "KEYWORD": "TITLES",
            "EXPRESSION": expression,
        })

    return result


def _build_final_forecast_rows(
    forecast_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
    product_names: dict[int, str],
) -> list[dict[str, Any]]:
    """Generate Section 4 ARIES forecast rows from PHD_FORCAST.

    Builder guide §4 + line-grammar + calculations reference:
    - Precede each property's forecast with ``START`` when a start date is available.
    - Phase keyword for the first segment of a product; ``"`` for continuations.
    - Decline convention: convert nominal DI to effective annual per calculations ref.
    - Exponential (b=0): ``<qi> X <unit> TO LIFE EXP <di_eff_annual>``
    - Hyperbolic (b>0): ``<qi> X <unit> TO LIFE B/<b> <di_eff_annual>``
    - Hyperbolic with Dmin: paired terminal-switch rows per grammar ref.
    """
    scoped = _filter_rows_by_lease(forecast_rows, selected_lease_ids)
    scoped = [row for row in scoped if _has_nonzero_forecast(row)]
    result: list[dict[str, Any]] = []

    # Group by lease to emit START and per-product phase keywords
    from itertools import groupby
    sorted_rows = sorted(scoped, key=_forecast_sort_key)
    for lease_id, lease_group in groupby(sorted_rows, key=_lease_id):
        propnum = _propnum_for_lease(lease_id)
        lease_rows_list = list(lease_group)

        # Emit START if any row has a start date
        start_date = ""
        for row in lease_rows_list:
            start_date = _clean_value(_row_get(
                row, "START_DTTM", "STARTDATE", "START_DATE", default="",
            ))
            if start_date:
                break
        if start_date:
            result.append({
                "PROPNUM": propnum, "SECTION": 4, "SEQUENCE": 0,
                "QUALIFIER": "", "KEYWORD": "START",
                "EXPRESSION": start_date,
            })

        # Track which phase keywords have been emitted for ditto handling
        emitted_phases: set[str] = set()

        for row in lease_rows_list:
            product_code = _product_code(row)
            qi = _to_float(_row_get(row, "Q", "QI", "RATE"))
            di = _to_float(_row_get(row, "DI", "DECLINE"))
            b = _to_float(_row_get(row, "B", "EXPONENT"))
            dmin = _to_float(_row_get(row, "D_MIN", "DMIN"))

            phase_kw = PRODUCT_ARIES_KEYWORD.get(product_code)
            unit = PRODUCT_RATE_UNIT.get(product_code)
            if not phase_kw or not unit or qi <= 0:
                continue

            # First row for this phase uses the phase keyword; continuations use "
            if phase_kw in emitted_phases:
                keyword = '"'
            else:
                keyword = phase_kw
                emitted_phases.add(phase_kw)

            # Convert nominal decline to effective annual (calculations ref)
            di_eff = _nominal_to_effective_annual(di, b)
            di_eff_pct = _format_decline_pct(di_eff)

            if b > 0 and dmin > 0:
                # Hyperbolic with terminal Dmin — paired terminal-switch (grammar ref)
                # Line 1: <qi> X <unit> <dmin_eff> EXP B/<b> <di_eff>
                # Line 2: X 0 <unit> X AD EXP <dmin_eff>
                dmin_eff = _nominal_to_effective_annual(dmin, 0.0)
                dmin_eff_pct = _format_decline_pct(dmin_eff)
                expression = f"{qi:.1f} X {unit} {dmin_eff_pct} EXP B/{b:.4f} {di_eff_pct}"
                result.append({
                    "PROPNUM": propnum, "SECTION": 4, "SEQUENCE": 0,
                    "QUALIFIER": "", "KEYWORD": keyword,
                    "EXPRESSION": expression,
                })
                term_expr = f"X 0 {unit} X AD EXP {dmin_eff_pct}"
                result.append({
                    "PROPNUM": propnum, "SECTION": 4, "SEQUENCE": 0,
                    "QUALIFIER": "", "KEYWORD": '"',
                    "EXPRESSION": term_expr,
                })
            elif b > 0:
                # Hyperbolic without Dmin (grammar ref: Arps form)
                expression = f"{qi:.1f} X {unit} TO LIFE B/{b:.4f} {di_eff_pct}"
                result.append({
                    "PROPNUM": propnum, "SECTION": 4, "SEQUENCE": 0,
                    "QUALIFIER": "", "KEYWORD": keyword,
                    "EXPRESSION": expression,
                })
            else:
                # Exponential b=0 (grammar ref: EXP form)
                expression = f"{qi:.1f} X {unit} TO LIFE EXP {di_eff_pct}"
                result.append({
                    "PROPNUM": propnum, "SECTION": 4, "SEQUENCE": 0,
                    "QUALIFIER": "", "KEYWORD": keyword,
                    "EXPRESSION": expression,
                })

    return result


def _build_final_price_rows(
    prodval_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
    product_names: dict[int, str],
) -> list[dict[str, Any]]:
    """Generate Section 5 ARIES price rows from PHD_LSEPRODVAL.

    Builder guide §5 + keyword catalog:
    ``PRI/<phase> <value> X <unit> TO LIFE PC 0``
    Use PC 0 for flat/no escalation per best practices.
    """
    scoped = _filter_rows_by_lease(prodval_rows, selected_lease_ids)
    result: list[dict[str, Any]] = []

    for row in sorted(scoped, key=_generic_source_sort_key):
        lease_id = _lease_id(row)
        propnum = _propnum_for_lease(lease_id)
        price = _to_float(_row_get(row, "PRICE", "VALUE"))
        product_code = _product_code(row)

        if price <= 0:
            continue

        phase = PRODUCT_ARIES_KEYWORD.get(product_code, "OIL")
        price_unit = PRODUCT_PRICE_UNIT.get(product_code, "$/B")
        keyword = f"PRI/{phase}"
        expression = f"{price:.2f} X {price_unit} TO LIFE PC 0"
        result.append({
            "PROPNUM": propnum, "SECTION": 5, "SEQUENCE": 0,
            "QUALIFIER": "", "KEYWORD": keyword,
            "EXPRESSION": expression,
        })

    return result


def _build_primary_product_by_lease(
    forecast_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
) -> dict[int, int]:
    """Determine each lease's primary product code from its highest-rate forecast row."""
    scoped = _filter_rows_by_lease(forecast_rows, selected_lease_ids)
    best: dict[int, tuple[float, int]] = {}
    for row in scoped:
        lid = _lease_id(row)
        qi = _to_float(_row_get(row, "Q", "QI", "RATE"))
        pc = _product_code(row)
        if pc > 0 and qi > 0:
            if lid not in best or qi > best[lid][0]:
                best[lid] = (qi, pc)
    return {lid: pc for lid, (_, pc) in best.items()}


def _build_final_expense_rows(
    econ_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
    primary_product_by_lease: dict[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Generate Section 6 ARIES expense rows from PHD_ECON.

    Builder guide §6 + keyword catalog:
    ``OPC/<phase> <cost> X $/B TO LIFE PC 0`` for per-unit variable costs.
    PHDWin OPCOST is treated as per-unit operating cost assigned to the
    primary product phase for the lease.
    Use PC 0 for flat/no escalation per best practices.
    """
    if primary_product_by_lease is None:
        primary_product_by_lease = {}
    scoped = _filter_rows_by_lease(econ_rows, selected_lease_ids)
    result: list[dict[str, Any]] = []

    for row in sorted(scoped, key=_generic_source_sort_key):
        lease_id = _lease_id(row)
        propnum = _propnum_for_lease(lease_id)
        opcost = _to_float(_row_get(row, "OPCOST", "FIXED_COST", "LOE", "VAR_COST"))

        if opcost <= 0:
            continue

        # Use the primary product phase for the lease; default to OIL
        primary_pc = primary_product_by_lease.get(lease_id, 2)
        phase = PRODUCT_ARIES_KEYWORD.get(primary_pc, "OIL")
        cost_unit = PRODUCT_PRICE_UNIT.get(primary_pc, "$/B")
        keyword = f"OPC/{phase}"

        expression = f"{opcost:.2f} X {cost_unit} TO LIFE PC 0"
        result.append({
            "PROPNUM": propnum, "SECTION": 6, "SEQUENCE": 0,
            "QUALIFIER": "", "KEYWORD": keyword,
            "EXPRESSION": expression,
        })

    return result


def _build_final_ownership_rows(
    owner_rows: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
) -> list[dict[str, Any]]:
    """Generate Section 7 ARIES ownership rows from PHD_OWNER.

    Builder guide §7 + keyword catalog:
    ``NET <wi%> <oil-nri%> <gas-nri%> %``
    Use first ownership row per lease (SEQ=1).
    """
    scoped = _filter_rows_by_lease(owner_rows, selected_lease_ids)
    result: list[dict[str, Any]] = []

    # Group by lease, take first sequence per lease
    seen_leases: set[int] = set()
    for row in sorted(scoped, key=_generic_source_sort_key):
        lease_id = _lease_id(row)
        if lease_id in seen_leases:
            continue
        seen_leases.add(lease_id)

        propnum = _propnum_for_lease(lease_id)
        wrkint = _to_float(_row_get(row, "WRKINT", "WI", "WORKING_INTEREST"))
        revint = _to_float(_row_get(row, "REVINT", "NRI", "NET_REVENUE_INTEREST", "LSENRI"))

        if wrkint <= 0 and revint <= 0:
            continue

        # ARIES ownership is in percent; PHDWin stores as fraction
        wi_pct = wrkint * 100.0 if wrkint <= 1.0 else wrkint
        ri_pct = revint * 100.0 if revint <= 1.0 else revint

        # NET <wi%> <nri%> %
        # PHDWin provides a single NRI; use the 2-value form per real ARIES data.
        # The 3-value form (oil-nri gas-nri) is used only when they differ.
        expression = f"{wi_pct:.5f} {ri_pct:.5f} %"
        result.append({
            "PROPNUM": propnum, "SECTION": 7, "SEQUENCE": 0,
            "QUALIFIER": "", "KEYWORD": "NET",
            "EXPRESSION": expression,
        })

    return result


def _build_final_invest_rows(
    invest_rows: list[dict[str, Any]],
    descriptions: list[dict[str, Any]],
    selected_lease_ids: set[int] | None,
) -> list[dict[str, Any]]:
    """Generate Section 8 ARIES investment rows from PHD_INVEST.

    Builder guide §8 + keyword catalog:
    ``<keyword> <tangible> <intangible> G <schedule> PC 0``
    For drilling, total goes in the intangible position (0 <amount> G).
    Schedule defaults to ``0 YRS`` when no date is available.
    """
    description_by_id = _build_invest_description_index(descriptions)
    scoped = _filter_rows_by_lease(invest_rows, selected_lease_ids)
    result: list[dict[str, Any]] = []

    for row in sorted(scoped, key=_generic_source_sort_key):
        lease_id = _lease_id(row)
        propnum = _propnum_for_lease(lease_id)
        amount = _to_float(_row_get(row, "AMOUNT", "COST", "CAPITAL"))
        tangible = _to_float(_row_get(row, "TANGIBLE"))
        intangible = _to_float(_row_get(row, "INTANGIBLE"))

        if amount <= 0 and tangible <= 0 and intangible <= 0:
            continue

        # Resolve investment keyword from description
        description_key = _row_key(row, INVEST_DESCRIPTION_ID_FIELDS)
        desc_row = description_by_id.get(description_key) if description_key else None
        desc_text = _description_text(desc_row).upper() if desc_row else ""
        keyword = INVEST_KEYWORD_MAP.get(desc_text, DEFAULT_INVEST_KEYWORD)

        # Use tangible/intangible split if available
        if tangible > 0 or intangible > 0:
            tang_val = tangible
            intang_val = intangible
        elif keyword == "DRILL":
            # Drilling costs are typically intangible
            tang_val = 0
            intang_val = amount
        else:
            tang_val = amount
            intang_val = 0

        # Schedule: use date if available, else 0 YRS
        inv_date = _clean_value(_row_get(row, "DATE_DTTM", "DATE", default=""))
        if inv_date:
            schedule = f"{inv_date} AD"
        else:
            schedule = "0 YRS"

        expression = f"{tang_val:.0f} {intang_val:.0f} G {schedule} PC 0"
        result.append({
            "PROPNUM": propnum, "SECTION": 8, "SEQUENCE": 0,
            "QUALIFIER": "", "KEYWORD": keyword,
            "EXPRESSION": expression,
        })

    return result


def _resequence_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort rows by PROPNUM, SECTION and assign contiguous SEQUENCE numbers."""
    sorted_rows = sorted(rows, key=lambda r: (r.get("PROPNUM", ""), r.get("SECTION", 0)))
    prev_key = None
    seq = 0
    for row in sorted_rows:
        key = (row.get("PROPNUM", ""), row.get("SECTION", 0))
        if key != prev_key:
            seq = 1
            prev_key = key
        else:
            seq += 1
        row["SEQUENCE"] = seq
    return sorted_rows


def build_ac_economic_rows(
    source_tables: dict[str, list[dict[str, Any]]],
    selected_lease_ids: set[int] | None = None,
) -> AcEconomicBuildResult:
    """Build AC_ECONOMIC rows from PHDWin source tables.

    Follows the builder pass order from ac-economic-builder-guide.md:
    1. Section 1: Titles from PHD_MAINLSE
    2. Section 4: Forecast from PHD_FORCAST (START, OIL, GAS, WTR)
    3. Section 5: Prices from PHD_LSEPRODVAL (PRI/<phase>)
    4. Section 6: Expenses from PHD_ECON (OPC/OIL)
    5. Section 7: Ownership from PHD_OWNER (NET)
    6. Section 8: Investments from PHD_INVEST (DRILL, CAPITAL)
    7. Resequence by PROPNUM + SECTION

    Tables routed elsewhere (not AC_ECONOMIC):
    - MOD_SCEN / MOD_TEMPLATE → AC_SCENARIO + qualifier selection
    - PHD_CUMVOL → AC_PROPERTY PRIOR_OIL/GAS/WTR
    - PHD_LSESEGMENT → merged into forecast context
    """
    CANONICAL_COLS = {"PROPNUM", "SECTION", "SEQUENCE", "QUALIFIER", "KEYWORD", "EXPRESSION"}

    normalized = {name.upper(): rows for name, rows in source_tables.items()}

    # Source table inventory
    economic_tables = [
        "PHD_MAINLSE", "PHD_FORCAST", "PHD_ECON", "PHD_INVEST",
        "PHD_INVESTDESCR", "PHD_LSEPRODVAL", "PHD_OWNER",
    ]
    routed_tables = ["MOD_SCEN", "MOD_TEMPLATE", "PHD_CUMVOL", "PHD_LSESEGMENT"]
    table_counts = {
        table: len(normalized.get(table, []))
        for table in economic_tables + routed_tables + ["PHD_PRODUCTNAMES"]
    }
    missing_lease_id_counts = {
        table: sum(1 for row in normalized.get(table, []) if _lease_id(row) <= 0)
        for table in economic_tables
        if table not in ("PHD_INVESTDESCR",)
    }

    product_names = _build_product_name_index(normalized.get("PHD_PRODUCTNAMES", []))

    # ── Build final ARIES rows per builder guide pass order ──

    # §1 Titles
    title_rows = _build_final_title_rows(
        normalized.get("PHD_MAINLSE", []),
        selected_lease_ids,
    )
    # §4 Forecast (includes START lines)
    forecast_source = normalized.get("PHD_FORCAST", [])
    forecast_rows = _build_final_forecast_rows(
        forecast_source,
        selected_lease_ids,
        product_names,
    )
    # §5 Prices
    price_rows = _build_final_price_rows(
        normalized.get("PHD_LSEPRODVAL", []),
        selected_lease_ids,
        product_names,
    )
    # §6 Expenses — use primary product phase per lease for keyword selection
    primary_product_by_lease = _build_primary_product_by_lease(
        forecast_source, selected_lease_ids,
    )
    expense_rows = _build_final_expense_rows(
        normalized.get("PHD_ECON", []),
        selected_lease_ids,
        primary_product_by_lease,
    )
    # §7 Ownership
    ownership_rows = _build_final_ownership_rows(
        normalized.get("PHD_OWNER", []),
        selected_lease_ids,
    )
    # §8 Investments
    invest_rows = _build_final_invest_rows(
        normalized.get("PHD_INVEST", []),
        normalized.get("PHD_INVESTDESCR", []),
        selected_lease_ids,
    )

    # ── Combine, resequence, strip to canonical columns ──

    all_rows = (
        title_rows + forecast_rows + price_rows
        + expense_rows + ownership_rows + invest_rows
    )
    all_rows = _resequence_rows(all_rows)
    all_rows = [{k: v for k, v in row.items() if k in CANONICAL_COLS} for row in all_rows]

    # ── Status and diagnostics ──

    status = ECONOMIC_STATUS_FINAL_ROWS_PRESENT if all_rows else ECONOMIC_STATUS_EMPTY

    warnings: list[str] = []
    if not normalized.get("PHD_FORCAST"):
        warnings.append("PHD_FORCAST is missing; no forecast rows generated.")
    missing_lease_tables = [
        f"{table}={count}"
        for table, count in missing_lease_id_counts.items()
        if count
    ]
    if missing_lease_tables:
        warnings.append(
            "Source rows without usable LSE_ID were skipped: "
            + ", ".join(missing_lease_tables)
            + "."
        )
    routed_notes: list[str] = []
    if table_counts.get("MOD_SCEN", 0):
        routed_notes.append(f"MOD_SCEN ({table_counts['MOD_SCEN']} rows) → AC_SCENARIO")
    if table_counts.get("MOD_TEMPLATE", 0):
        routed_notes.append(f"MOD_TEMPLATE ({table_counts['MOD_TEMPLATE']} rows) → AC_SCENARIO")
    if table_counts.get("PHD_CUMVOL", 0):
        routed_notes.append(f"PHD_CUMVOL ({table_counts['PHD_CUMVOL']} rows) → AC_PROPERTY PRIOR_*")
    if table_counts.get("PHD_LSESEGMENT", 0):
        routed_notes.append(f"PHD_LSESEGMENT ({table_counts['PHD_LSESEGMENT']} rows) → forecast context")
    if routed_notes:
        warnings.append(
            "Source tables routed to other destinations (not AC_ECONOMIC): "
            + "; ".join(routed_notes)
            + "."
        )

    return AcEconomicBuildResult(
        rows=all_rows,
        warnings=warnings,
        diagnostics={
            "tableCounts": table_counts,
            "missingLeaseIdCounts": missing_lease_id_counts,
            "productNameCount": len(product_names),
            "selectedLeaseIds": sorted(selected_lease_ids) if selected_lease_ids else None,
            "titleRowCount": len(title_rows),
            "forecastRowCount": len(forecast_rows),
            "priceRowCount": len(price_rows),
            "expenseRowCount": len(expense_rows),
            "ownershipRowCount": len(ownership_rows),
            "investRowCount": len(invest_rows),
            "totalRowCount": len(all_rows),
            "status": status,
        },
    )
