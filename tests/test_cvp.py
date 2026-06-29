"""CVP / break-even-point tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cvp import calc


def _approx(a, b, eps=1e-6):
    assert abs(a - b) < eps, f"{a} vs {b}"


def test_basic_bep():
    # 売上 1,000,000 / 変動費 600,000 / 固定費 300,000
    # 限界利益 400,000、限界利益率 0.4、BEP = 300,000 / 0.4 = 750,000
    r = calc(sales=1_000_000, variable_cost=600_000, fixed_cost=300_000)
    _approx(r.cm, 400_000)
    _approx(r.cm_ratio, 0.4)
    _approx(r.bep_sales, 750_000)
    _approx(r.margin_of_safety, 250_000)
    _approx(r.margin_of_safety_ratio, 0.25)


def test_bep_shift_with_variance_as_fixed():
    # 不利差異 80,000 を固定費に加算
    # 調整後固定費 380,000、BEP = 380,000 / 0.4 = 950,000、シフト幅 +200,000
    r = calc(sales=1_000_000, variable_cost=600_000, fixed_cost=300_000, additional_fixed=80_000)
    _approx(r.adjusted_fixed, 380_000)
    _approx(r.adjusted_bep_sales, 950_000)
    _approx(r.bep_shift, 200_000)
    _approx(r.adjusted_margin_of_safety, 50_000)


def test_zero_sales_handles_gracefully():
    r = calc(sales=0, variable_cost=0, fixed_cost=1_000)
    _approx(r.cm_ratio, 0.0)
    _approx(r.bep_sales, 0.0)


if __name__ == "__main__":
    test_basic_bep()
    test_bep_shift_with_variance_as_fixed()
    test_zero_sales_handles_gracefully()
    print("cvp tests OK")
