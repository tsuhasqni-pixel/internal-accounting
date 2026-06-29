"""CVP / break-even calculations, including the variance-as-fixed-cost shift.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CVPResult:
    sales: float
    variable_cost: float
    fixed_cost: float
    cm: float
    cm_ratio: float
    bep_sales: float
    margin_of_safety: float
    margin_of_safety_ratio: float

    additional_fixed: float
    adjusted_fixed: float
    adjusted_bep_sales: float
    bep_shift: float
    adjusted_margin_of_safety: float


def calc(sales: float, variable_cost: float, fixed_cost: float,
         additional_fixed: float = 0.0) -> CVPResult:
    cm = sales - variable_cost
    cm_ratio = cm / sales if sales else 0.0

    bep_sales = (fixed_cost / cm_ratio) if cm_ratio > 0 else 0.0
    margin = sales - bep_sales
    margin_ratio = margin / sales if sales else 0.0

    adjusted_fixed = fixed_cost + additional_fixed
    adjusted_bep = (adjusted_fixed / cm_ratio) if cm_ratio > 0 else 0.0
    bep_shift = adjusted_bep - bep_sales
    adjusted_margin = sales - adjusted_bep

    return CVPResult(
        sales=sales,
        variable_cost=variable_cost,
        fixed_cost=fixed_cost,
        cm=cm,
        cm_ratio=cm_ratio,
        bep_sales=bep_sales,
        margin_of_safety=margin,
        margin_of_safety_ratio=margin_ratio,
        additional_fixed=additional_fixed,
        adjusted_fixed=adjusted_fixed,
        adjusted_bep_sales=adjusted_bep,
        bep_shift=bep_shift,
        adjusted_margin_of_safety=adjusted_margin,
    )
