"""Numerical sanity tests for the variance engine.

Sign convention: positive = unfavorable (actual cost > standard).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import (
    Actual,
    BOMItem,
    CostCard,
    LaborActual,
    LaborStd,
    MaterialActual,
    OHActual,
    OHStd,
    Product,
    SimpleActual,
    SimpleBudget,
)
from core.variance import calc, calc_detailed, calc_simple, unfavorable_total


def _approx(a, b, eps=1e-6):
    assert abs(a - b) < eps, f"{a} vs {b}"


def test_material_variance_textbook_example():
    """標準単価 100、実際 110、標準消費 50、実際 55（生産量1個、標準1個）。

    価格差異 = (110 − 100) × 55 = +550（不利）
    数量差異 = (55 − 50) × 100 = +500（不利）
    """
    product = Product(
        id="P1",
        name="Test",
        mode="detailed",
        std_output=1.0,
        cost_card=CostCard(
            materials=[BOMItem(name="鋼材A", std_price=100, std_qty=50)],
        ),
    )
    actual = Actual(
        product_id="P1",
        period="2026-Q1",
        actual_output=1.0,
        materials=[MaterialActual(name="鋼材A", actual_price=110, actual_qty=55)],
    )
    report = calc_detailed(product, actual)
    by_name = {line.name: line.value for line in report.lines}
    _approx(by_name["材料価格差異 (鋼材A)"], 550)
    _approx(by_name["材料数量差異 (鋼材A)"], 500)


def test_labor_variance():
    """標準賃率 1200、実際 1250、標準時間 10h、実際 11h。

    賃率差異 = (1250 − 1200) × 11 = +550（不利）
    時間差異 = (11 − 10) × 1200 = +1200（不利）
    """
    product = Product(
        id="P2", name="L", mode="detailed", std_output=1.0,
        cost_card=CostCard(labors=[LaborStd(process="加工", std_rate=1200, std_hours=10)]),
    )
    actual = Actual(
        product_id="P2", period="2026-Q1", actual_output=1.0,
        labors=[LaborActual(process="加工", actual_rate=1250, actual_hours=11)],
    )
    report = calc_detailed(product, actual)
    by_name = {line.name: line.value for line in report.lines}
    _approx(by_name["労務賃率差異 (加工)"], 550)
    _approx(by_name["労務時間差異 (加工)"], 1200)


def test_overhead_3way():
    """変動率 500、固定予算 100,000、基準操業度 100h、実際時間 110h、
    標準時間 90h（output換算後）、実際変動 60,000、実際固定 105,000。

    変動OH予算差異 = 60,000 − 500 × 110 = +5,000（不利）
    変動OH能率差異 = 500 × (110 − 90) = +10,000（不利）
    固定OH予算差異 = 105,000 − 100,000 = +5,000（不利）
    固定OH操業度差異 = 100,000 − (100,000/100) × 90 = +10,000（不利、操業度未達）
    """
    product = Product(
        id="P3", name="OH", mode="detailed", std_output=1.0,
        cost_card=CostCard(
            labors=[LaborStd(process="工程", std_rate=0, std_hours=90)],
            overhead=OHStd(var_rate=500, fixed_budget=100_000, normal_hours=100),
        ),
    )
    actual = Actual(
        product_id="P3", period="2026-Q1", actual_output=1.0,
        labors=[LaborActual(process="工程", actual_rate=0, actual_hours=110)],
        overhead=OHActual(actual_variable=60_000, actual_fixed=105_000),
    )
    report = calc_detailed(product, actual)
    by_name = {line.name: line.value for line in report.lines}
    _approx(by_name["変動OH予算差異"], 5_000)
    _approx(by_name["変動OH能率差異"], 10_000)
    _approx(by_name["固定OH予算差異"], 5_000)
    _approx(by_name["固定OH操業度差異"], 10_000)


def test_simple_mode_total_variance():
    product = Product(
        id="C1", name="案件A", mode="simple", std_output=1.0,
        cost_card=CostCard(simple_budget=SimpleBudget(total=10_000_000)),
    )
    actual = Actual(
        product_id="C1", period="2026-Q1", actual_output=1.0,
        simple=SimpleActual(total=10_500_000),
    )
    report = calc_simple(product, actual)
    _approx(report.total_variance, 500_000)
    _approx(unfavorable_total(report), 500_000)


def test_dispatch_calc_chooses_mode():
    product = Product(
        id="X", name="X", mode="simple", std_output=1.0,
        cost_card=CostCard(simple_budget=SimpleBudget(total=100)),
    )
    actual = Actual(
        product_id="X", period="2026-Q1", actual_output=1.0,
        simple=SimpleActual(total=120),
    )
    assert calc(product, actual).mode == "simple"


def test_output_scaling_for_std_qty():
    """標準は5個セット, 実生産量10個 → 標準消費量は2倍に展開される."""
    product = Product(
        id="S", name="S", mode="detailed", std_output=5.0,
        cost_card=CostCard(materials=[BOMItem(name="m", std_price=100, std_qty=20)]),
    )
    actual = Actual(
        product_id="S", period="2026-Q1", actual_output=10.0,
        materials=[MaterialActual(name="m", actual_price=100, actual_qty=42)],
    )
    report = calc_detailed(product, actual)
    by_name = {line.name: line.value for line in report.lines}
    _approx(by_name["材料価格差異 (m)"], 0)
    _approx(by_name["材料数量差異 (m)"], (42 - 40) * 100)


if __name__ == "__main__":
    test_material_variance_textbook_example()
    test_labor_variance()
    test_overhead_3way()
    test_simple_mode_total_variance()
    test_dispatch_calc_chooses_mode()
    test_output_scaling_for_std_qty()
    print("variance tests OK")
