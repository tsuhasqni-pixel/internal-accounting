"""Domain models for the internal management-accounting tool.

All numeric fields are plain floats; rounding/formatting is handled in
``reports.py``. Records are JSON-serialisable via ``dataclasses.asdict``.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


CostMode = Literal["detailed", "simple"]


@dataclass
class BOMItem:
    name: str
    std_price: float
    std_qty: float


@dataclass
class LaborStd:
    process: str
    std_rate: float
    std_hours: float


@dataclass
class OHStd:
    var_rate: float = 0.0
    fixed_budget: float = 0.0
    normal_hours: float = 0.0


@dataclass
class SimpleBudget:
    total: float = 0.0
    material: float = 0.0
    labor: float = 0.0
    overhead: float = 0.0


@dataclass
class CostCard:
    materials: list[BOMItem] = field(default_factory=list)
    labors: list[LaborStd] = field(default_factory=list)
    overhead: OHStd = field(default_factory=OHStd)
    simple_budget: SimpleBudget = field(default_factory=SimpleBudget)


@dataclass
class Product:
    id: str
    name: str
    mode: CostMode = "detailed"
    unit: str = "個"
    std_output: float = 1.0
    cost_card: CostCard = field(default_factory=CostCard)


@dataclass
class MaterialActual:
    name: str
    actual_price: float
    actual_qty: float


@dataclass
class LaborActual:
    process: str
    actual_rate: float
    actual_hours: float


@dataclass
class OHActual:
    actual_variable: float = 0.0
    actual_fixed: float = 0.0


@dataclass
class SimpleActual:
    total: float = 0.0
    material: float = 0.0
    labor: float = 0.0
    overhead: float = 0.0


@dataclass
class Actual:
    product_id: str
    period: str
    actual_output: float = 1.0
    materials: list[MaterialActual] = field(default_factory=list)
    labors: list[LaborActual] = field(default_factory=list)
    overhead: OHActual = field(default_factory=OHActual)
    simple: SimpleActual = field(default_factory=SimpleActual)


@dataclass
class CVPInput:
    sales: float
    variable_cost: float
    fixed_cost: float
    include_variance_product_ids: list[str] = field(default_factory=list)
    include_variance_period: str = ""


def dump(obj) -> dict:
    return asdict(obj)
