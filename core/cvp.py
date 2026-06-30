"""CVP / segment-margin / break-even calculations.

Sales and variable cost are entered per product line; the result includes
per-line and blended (company-wide) metrics, including the stepped contribution
margin (限界利益 → 個別固定費 → 貢献利益 → 共通固定費 → 営業利益).
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import CVPLine, Product


@dataclass
class CVPLineResult:
    name: str
    product_id: str
    unit_price: float
    quantity: float
    unit_variable: float
    direct_fixed: float
    sales: float
    variable_cost: float
    cm: float
    cm_ratio: float
    segment_margin: float


@dataclass
class CVPResult:
    lines: list[CVPLineResult]
    total_sales: float
    total_variable_cost: float
    total_cm: float
    cm_ratio: float
    total_direct_fixed: float
    total_segment_margin: float
    common_fixed: float
    operating_income: float
    total_fixed: float
    bep_sales: float
    margin_of_safety: float
    margin_of_safety_ratio: float


def _line(line: CVPLine) -> CVPLineResult:
    sales = line.unit_price * line.quantity
    vc = line.unit_variable * line.quantity
    cm = sales - vc
    return CVPLineResult(
        name=line.name or line.product_id or "(無名)",
        product_id=line.product_id,
        unit_price=line.unit_price,
        quantity=line.quantity,
        unit_variable=line.unit_variable,
        direct_fixed=line.direct_fixed,
        sales=sales,
        variable_cost=vc,
        cm=cm,
        cm_ratio=(cm / sales) if sales else 0.0,
        segment_margin=cm - line.direct_fixed,
    )


def calc(lines: list[CVPLine], common_fixed: float = 0.0) -> CVPResult:
    line_results = [_line(l) for l in lines]
    total_sales = sum(l.sales for l in line_results)
    total_vc = sum(l.variable_cost for l in line_results)
    total_cm = total_sales - total_vc
    cm_ratio = (total_cm / total_sales) if total_sales else 0.0
    total_direct = sum(l.direct_fixed for l in line_results)
    total_seg = total_cm - total_direct
    operating_income = total_seg - common_fixed
    total_fixed = total_direct + common_fixed
    bep = (total_fixed / cm_ratio) if cm_ratio > 0 else 0.0
    mos = total_sales - bep
    mos_ratio = (mos / total_sales) if total_sales else 0.0
    return CVPResult(
        lines=line_results,
        total_sales=total_sales,
        total_variable_cost=total_vc,
        total_cm=total_cm,
        cm_ratio=cm_ratio,
        total_direct_fixed=total_direct,
        total_segment_margin=total_seg,
        common_fixed=common_fixed,
        operating_income=operating_income,
        total_fixed=total_fixed,
        bep_sales=bep,
        margin_of_safety=mos,
        margin_of_safety_ratio=mos_ratio,
    )


def pull_unit_variable_cost(product: Product) -> float:
    """Compute per-unit variable cost from a product's standard cost card.

    detailed: DM + DL + variable OH per unit (fixed OH excluded).
    simple:   simple_budget.total / std_output (treats budget as variable).
    """
    out = product.std_output if product.std_output > 0 else 1.0
    if product.mode == "simple":
        return product.cost_card.simple_budget.total / out
    cc = product.cost_card
    unit_dm = sum(m.std_price * m.std_qty for m in cc.materials) / out
    unit_dl = sum(l.std_rate * l.std_hours for l in cc.labors) / out
    total_std_hours_per_unit = sum(l.std_hours for l in cc.labors) / out
    unit_voh = cc.overhead.var_rate * total_std_hours_per_unit
    return unit_dm + unit_dl + unit_voh
