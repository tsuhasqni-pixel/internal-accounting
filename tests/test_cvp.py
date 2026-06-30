"""CVP / segment-margin / break-even tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cvp import calc, pull_unit_variable_cost
from core.models import (
    BOMItem,
    CostCard,
    CVPLine,
    LaborStd,
    OHStd,
    Product,
    SimpleBudget,
)


def _approx(a, b, eps=1e-6):
    assert abs(a - b) < eps, f"{a} vs {b}"


def test_single_line_basic():
    """1ライン: 売上 1,000,000 / 変動費 600,000 / 固定費 300,000 → BEP 750,000."""
    r = calc([CVPLine(name="P", unit_price=1_000_000, quantity=1, unit_variable=600_000)], common_fixed=300_000)
    _approx(r.total_sales, 1_000_000)
    _approx(r.total_cm, 400_000)
    _approx(r.cm_ratio, 0.4)
    _approx(r.bep_sales, 750_000)
    _approx(r.margin_of_safety, 250_000)
    _approx(r.operating_income, 100_000)


def test_two_lines_segment_margin_textbook():
    """A: 単価 1,000 × 100個、単位変動費 600、個別固定費 20,000
    B: 単価 2,000 × 50個、単位変動費 1,200、個別固定費 30,000
    共通固定費 50,000

    A: 売上 100,000 / 変動費 60,000 / 限界利益 40,000 / 貢献利益 20,000
    B: 売上 100,000 / 変動費 60,000 / 限界利益 40,000 / 貢献利益 10,000
    合計: CM 80,000 / CM率 0.4 / 段階合計 30,000 / 営業利益 -20,000
    BEP = (20,000 + 30,000 + 50,000) / 0.4 = 250,000
    """
    r = calc(
        [
            CVPLine(name="A", unit_price=1_000, quantity=100, unit_variable=600, direct_fixed=20_000),
            CVPLine(name="B", unit_price=2_000, quantity=50, unit_variable=1_200, direct_fixed=30_000),
        ],
        common_fixed=50_000,
    )
    a, b = r.lines
    _approx(a.cm, 40_000); _approx(a.segment_margin, 20_000)
    _approx(b.cm, 40_000); _approx(b.segment_margin, 10_000)
    _approx(r.total_cm, 80_000); _approx(r.cm_ratio, 0.4)
    _approx(r.total_segment_margin, 30_000)
    _approx(r.operating_income, -20_000)
    _approx(r.total_fixed, 100_000)
    _approx(r.bep_sales, 250_000)
    _approx(r.margin_of_safety, -50_000)


def test_empty_scenario_safe():
    r = calc([], common_fixed=0.0)
    _approx(r.total_sales, 0)
    _approx(r.bep_sales, 0)
    _approx(r.operating_income, 0)


def test_pull_unit_variable_cost_detailed():
    """detailed: DM+DL+変動OH を std_output で割って 1単位あたり。

    std_output=10、材料: 100×50=5,000、労務: 1,000×8=8,000、変動率 200、労務時間 8
    → unit_DM=500, unit_DL=800, unit_VOH = 200 * 8/10 = 160
    → unit_variable = 1,460
    """
    p = Product(
        id="X", name="X", mode="detailed", std_output=10,
        cost_card=CostCard(
            materials=[BOMItem(name="m", std_price=100, std_qty=50)],
            labors=[LaborStd(process="l", std_rate=1_000, std_hours=8)],
            overhead=OHStd(var_rate=200, fixed_budget=10_000, normal_hours=10),
        ),
    )
    _approx(pull_unit_variable_cost(p), 1_460)


def test_pull_unit_variable_cost_simple():
    p = Product(
        id="C", name="案件", mode="simple", std_output=5,
        cost_card=CostCard(simple_budget=SimpleBudget(total=500_000)),
    )
    _approx(pull_unit_variable_cost(p), 100_000)


if __name__ == "__main__":
    test_single_line_basic()
    test_two_lines_segment_margin_textbook()
    test_empty_scenario_safe()
    test_pull_unit_variable_cost_detailed()
    test_pull_unit_variable_cost_simple()
    print("cvp tests OK")
