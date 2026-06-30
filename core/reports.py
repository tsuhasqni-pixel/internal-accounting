"""Helpers to shape calculation results for the HTML templates."""
from __future__ import annotations

from dataclasses import asdict

from .cvp import CVPResult
from .variance import VarianceReport


def yen(v: float) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}¥{abs(v):,.0f}"


def signed_yen(v: float) -> str:
    if v > 0:
        return f"+¥{v:,.0f}"
    if v < 0:
        return f"-¥{abs(v):,.0f}"
    return "¥0"


def pct(v: float) -> str:
    return f"{v * 100:,.2f}%"


def variance_to_view(report: VarianceReport) -> dict:
    rows = []
    for line in report.lines:
        rows.append({
            "name": line.name,
            "value": line.value,
            "formatted": signed_yen(line.value),
            "sign": line.sign,
            "label": "不利" if line.sign == "unfav" else ("有利" if line.sign == "fav" else "—"),
            "detail": line.detail,
        })
    return {
        "product_id": report.product_id,
        "period": report.period,
        "mode": report.mode,
        "rows": rows,
        "total_actual": yen(report.total_actual),
        "total_standard": yen(report.total_standard_for_output),
        "total_variance": signed_yen(report.total_variance),
        "total_variance_sign": (
            "unfav" if report.total_variance > 0
            else "fav" if report.total_variance < 0
            else "zero"
        ),
        "total_variance_label": (
            "不利" if report.total_variance > 0
            else "有利" if report.total_variance < 0
            else "—"
        ),
    }


def cvp_to_view(result: CVPResult) -> dict:
    lines = []
    for l in result.lines:
        lines.append({
            "name": l.name,
            "product_id": l.product_id,
            "unit_price_fmt": yen(l.unit_price),
            "quantity": l.quantity,
            "unit_variable_fmt": yen(l.unit_variable),
            "direct_fixed_fmt": yen(l.direct_fixed),
            "sales_fmt": yen(l.sales),
            "variable_cost_fmt": yen(l.variable_cost),
            "cm_fmt": yen(l.cm),
            "cm_ratio_fmt": pct(l.cm_ratio),
            "segment_margin_fmt": yen(l.segment_margin),
            "segment_margin_sign": (
                "fav" if l.segment_margin > 0
                else "unfav" if l.segment_margin < 0
                else "zero"
            ),
        })
    return {
        "lines": lines,
        "total_sales_fmt": yen(result.total_sales),
        "total_variable_cost_fmt": yen(result.total_variable_cost),
        "total_cm_fmt": yen(result.total_cm),
        "cm_ratio_fmt": pct(result.cm_ratio),
        "total_direct_fixed_fmt": yen(result.total_direct_fixed),
        "total_segment_margin_fmt": yen(result.total_segment_margin),
        "common_fixed_fmt": yen(result.common_fixed),
        "operating_income_fmt": yen(result.operating_income),
        "operating_income_sign": (
            "fav" if result.operating_income > 0
            else "unfav" if result.operating_income < 0
            else "zero"
        ),
        "total_fixed_fmt": yen(result.total_fixed),
        "bep_sales_fmt": yen(result.bep_sales),
        "margin_of_safety_fmt": yen(result.margin_of_safety),
        "margin_of_safety_ratio_fmt": pct(result.margin_of_safety_ratio),
        "total_sales": result.total_sales,
        "total_variable_cost": result.total_variable_cost,
        "total_fixed": result.total_fixed,
        "bep_sales": result.bep_sales,
        "cm_ratio": result.cm_ratio,
    }
