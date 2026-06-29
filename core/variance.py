"""Cost-variance calculations.

Sign convention: a positive value is **unfavorable** (cost overrun), a negative
value is **favorable** (cost savings). This matches the Japanese textbook
convention of treating ``実際 − 標準`` as the variance from the cost side.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import Actual, Product


VarianceSign = Literal["unfav", "fav", "zero"]


@dataclass
class VarianceLine:
    name: str
    value: float
    detail: str = ""

    @property
    def sign(self) -> VarianceSign:
        if self.value > 0:
            return "unfav"
        if self.value < 0:
            return "fav"
        return "zero"


@dataclass
class VarianceReport:
    product_id: str
    period: str
    mode: str
    lines: list[VarianceLine]
    total_actual: float
    total_standard_for_output: float
    total_variance: float


def _std_qty_for_output(std_qty_per_unit: float, std_output: float, actual_output: float) -> float:
    """Allow the cost card to be entered per ``std_output`` units (default 1).

    Standard quantity for the realised production volume is then
    ``std_qty_per_unit / std_output * actual_output``.
    """
    if std_output <= 0:
        return 0.0
    return std_qty_per_unit / std_output * actual_output


def calc_detailed(product: Product, actual: Actual) -> VarianceReport:
    cc = product.cost_card
    lines: list[VarianceLine] = []
    total_actual = 0.0
    total_standard = 0.0

    actual_by_name = {m.name: m for m in actual.materials}
    std_by_name = {m.name: m for m in cc.materials}
    material_names = list(dict.fromkeys(
        [m.name for m in cc.materials] + [m.name for m in actual.materials]
    ))

    for name in material_names:
        std = std_by_name.get(name)
        act = actual_by_name.get(name)
        std_price = std.std_price if std else 0.0
        std_qty_unit = std.std_qty if std else 0.0
        act_price = act.actual_price if act else 0.0
        act_qty = act.actual_qty if act else 0.0
        sq_for_output = _std_qty_for_output(std_qty_unit, product.std_output, actual.actual_output)

        price_var = (act_price - std_price) * act_qty
        qty_var = (act_qty - sq_for_output) * std_price
        lines.append(VarianceLine(
            name=f"材料価格差異 ({name})",
            value=price_var,
            detail=f"(実{act_price:g} − 標{std_price:g}) × 実消費 {act_qty:g}",
        ))
        lines.append(VarianceLine(
            name=f"材料数量差異 ({name})",
            value=qty_var,
            detail=f"(実{act_qty:g} − 標{sq_for_output:g}) × 標単価 {std_price:g}",
        ))
        total_actual += act_price * act_qty
        total_standard += std_price * sq_for_output

    actual_labor_by_name = {l.process: l for l in actual.labors}
    std_labor_by_name = {l.process: l for l in cc.labors}
    labor_names = list(dict.fromkeys(
        [l.process for l in cc.labors] + [l.process for l in actual.labors]
    ))
    total_actual_hours = 0.0
    total_std_hours_for_output = 0.0
    for name in labor_names:
        std = std_labor_by_name.get(name)
        act = actual_labor_by_name.get(name)
        std_rate = std.std_rate if std else 0.0
        std_hours_unit = std.std_hours if std else 0.0
        act_rate = act.actual_rate if act else 0.0
        act_hours = act.actual_hours if act else 0.0
        sh_for_output = _std_qty_for_output(std_hours_unit, product.std_output, actual.actual_output)

        rate_var = (act_rate - std_rate) * act_hours
        time_var = (act_hours - sh_for_output) * std_rate
        lines.append(VarianceLine(
            name=f"労務賃率差異 ({name})",
            value=rate_var,
            detail=f"(実{act_rate:g} − 標{std_rate:g}) × 実時間 {act_hours:g}",
        ))
        lines.append(VarianceLine(
            name=f"労務時間差異 ({name})",
            value=time_var,
            detail=f"(実{act_hours:g} − 標{sh_for_output:g}) × 標賃率 {std_rate:g}",
        ))
        total_actual += act_rate * act_hours
        total_standard += std_rate * sh_for_output
        total_actual_hours += act_hours
        total_std_hours_for_output += sh_for_output

    oh = cc.overhead
    act_oh = actual.overhead
    var_oh_budget_var = act_oh.actual_variable - oh.var_rate * total_actual_hours
    var_oh_eff_var = oh.var_rate * (total_actual_hours - total_std_hours_for_output)
    fixed_oh_budget_var = act_oh.actual_fixed - oh.fixed_budget
    std_fixed_rate = (oh.fixed_budget / oh.normal_hours) if oh.normal_hours else 0.0
    fixed_oh_volume_var = oh.fixed_budget - std_fixed_rate * total_std_hours_for_output

    lines.append(VarianceLine(
        name="変動OH予算差異",
        value=var_oh_budget_var,
        detail=f"実{act_oh.actual_variable:g} − 標変動率{oh.var_rate:g} × 実時間{total_actual_hours:g}",
    ))
    lines.append(VarianceLine(
        name="変動OH能率差異",
        value=var_oh_eff_var,
        detail=f"標変動率{oh.var_rate:g} × (実時間{total_actual_hours:g} − 標時間{total_std_hours_for_output:g})",
    ))
    lines.append(VarianceLine(
        name="固定OH予算差異",
        value=fixed_oh_budget_var,
        detail=f"実{act_oh.actual_fixed:g} − 予算{oh.fixed_budget:g}",
    ))
    lines.append(VarianceLine(
        name="固定OH操業度差異",
        value=fixed_oh_volume_var,
        detail=f"予算{oh.fixed_budget:g} − 標固定率{std_fixed_rate:g} × 標時間{total_std_hours_for_output:g}",
    ))

    total_actual += act_oh.actual_variable + act_oh.actual_fixed
    total_standard += oh.var_rate * total_std_hours_for_output + std_fixed_rate * total_std_hours_for_output

    return VarianceReport(
        product_id=product.id,
        period=actual.period,
        mode="detailed",
        lines=lines,
        total_actual=total_actual,
        total_standard_for_output=total_standard,
        total_variance=total_actual - total_standard,
    )


def calc_simple(product: Product, actual: Actual) -> VarianceReport:
    sb = product.cost_card.simple_budget
    sa = actual.simple
    lines: list[VarianceLine] = []

    if sb.material or sa.material:
        lines.append(VarianceLine(
            name="材料費差異",
            value=sa.material - sb.material,
            detail=f"実{sa.material:g} − 予算{sb.material:g}",
        ))
    if sb.labor or sa.labor:
        lines.append(VarianceLine(
            name="労務費差異",
            value=sa.labor - sb.labor,
            detail=f"実{sa.labor:g} − 予算{sb.labor:g}",
        ))
    if sb.overhead or sa.overhead:
        lines.append(VarianceLine(
            name="経費差異",
            value=sa.overhead - sb.overhead,
            detail=f"実{sa.overhead:g} − 予算{sb.overhead:g}",
        ))

    actual_total = sa.total or (sa.material + sa.labor + sa.overhead)
    budget_total = sb.total or (sb.material + sb.labor + sb.overhead)
    lines.append(VarianceLine(
        name="総差異",
        value=actual_total - budget_total,
        detail=f"実{actual_total:g} − 予算{budget_total:g}",
    ))

    return VarianceReport(
        product_id=product.id,
        period=actual.period,
        mode="simple",
        lines=lines,
        total_actual=actual_total,
        total_standard_for_output=budget_total,
        total_variance=actual_total - budget_total,
    )


def calc(product: Product, actual: Actual) -> VarianceReport:
    if product.mode == "simple":
        return calc_simple(product, actual)
    return calc_detailed(product, actual)


def unfavorable_total(report: VarianceReport) -> float:
    """Sum of unfavorable variance lines (used for BEP-shift simulation).

    For ``simple`` mode we only count the explicit sub-lines (材料/労務/経費)
    when present; otherwise we count 総差異, to avoid double-counting.
    """
    if report.mode == "simple":
        has_split = any(l.name != "総差異" for l in report.lines)
        if has_split:
            return sum(l.value for l in report.lines if l.name != "総差異" and l.value > 0)
        return sum(l.value for l in report.lines if l.value > 0)
    return sum(l.value for l in report.lines if l.value > 0)
