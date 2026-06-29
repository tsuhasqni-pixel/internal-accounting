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
    d = asdict(result)
    d["sales_fmt"] = yen(result.sales)
    d["variable_cost_fmt"] = yen(result.variable_cost)
    d["fixed_cost_fmt"] = yen(result.fixed_cost)
    d["cm_fmt"] = yen(result.cm)
    d["cm_ratio_fmt"] = pct(result.cm_ratio)
    d["bep_sales_fmt"] = yen(result.bep_sales)
    d["margin_of_safety_fmt"] = yen(result.margin_of_safety)
    d["margin_of_safety_ratio_fmt"] = pct(result.margin_of_safety_ratio)
    d["additional_fixed_fmt"] = yen(result.additional_fixed)
    d["adjusted_fixed_fmt"] = yen(result.adjusted_fixed)
    d["adjusted_bep_sales_fmt"] = yen(result.adjusted_bep_sales)
    d["bep_shift_fmt"] = signed_yen(result.bep_shift)
    d["adjusted_margin_of_safety_fmt"] = yen(result.adjusted_margin_of_safety)
    return d
