"""JSON-backed persistence. One file per kind under ``data/``.

Atomic writes via tempfile + os.replace.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Actual, CVPLine, CVPScenario, Product, CostCard, BOMItem, LaborStd, OHStd, \
    SimpleBudget, MaterialActual, LaborActual, OHActual, SimpleActual


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"
ACTUALS_FILE = DATA_DIR / "actuals.json"
CVP_FILE = DATA_DIR / "cvp.json"


def _atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _product_from_dict(d: dict) -> Product:
    cc = d.get("cost_card", {}) or {}
    cost_card = CostCard(
        materials=[BOMItem(**m) for m in cc.get("materials", [])],
        labors=[LaborStd(**l) for l in cc.get("labors", [])],
        overhead=OHStd(**cc.get("overhead", {})),
        simple_budget=SimpleBudget(**cc.get("simple_budget", {})),
    )
    return Product(
        id=d["id"],
        name=d["name"],
        mode=d.get("mode", "detailed"),
        unit=d.get("unit", "個"),
        std_output=float(d.get("std_output", 1.0)),
        cost_card=cost_card,
    )


def _actual_from_dict(d: dict) -> Actual:
    return Actual(
        product_id=d["product_id"],
        period=d["period"],
        actual_output=float(d.get("actual_output", 1.0)),
        materials=[MaterialActual(**m) for m in d.get("materials", [])],
        labors=[LaborActual(**l) for l in d.get("labors", [])],
        overhead=OHActual(**d.get("overhead", {})),
        simple=SimpleActual(**d.get("simple", {})),
    )


def load_products() -> list[Product]:
    raw = _read_json(PRODUCTS_FILE, [])
    return [_product_from_dict(d) for d in raw]


def save_products(products: list[Product]) -> None:
    from dataclasses import asdict
    _atomic_write(PRODUCTS_FILE, [asdict(p) for p in products])


def load_actuals() -> list[Actual]:
    raw = _read_json(ACTUALS_FILE, [])
    return [_actual_from_dict(d) for d in raw]


def save_actuals(actuals: list[Actual]) -> None:
    from dataclasses import asdict
    _atomic_write(ACTUALS_FILE, [asdict(a) for a in actuals])


def _cvp_from_dict(d: dict) -> CVPScenario:
    # Migrate v1 shape {sales, variable_cost, fixed_cost, ...} → one-line scenario.
    if "lines" not in d and ("sales" in d or "variable_cost" in d or "fixed_cost" in d):
        return CVPScenario(
            lines=[CVPLine(
                name="（旧データ）合計",
                product_id="",
                unit_price=float(d.get("sales", 0)),
                quantity=1.0,
                unit_variable=float(d.get("variable_cost", 0)),
                direct_fixed=0.0,
            )],
            common_fixed=float(d.get("fixed_cost", 0)),
        )
    return CVPScenario(
        lines=[CVPLine(**l) for l in d.get("lines", [])],
        common_fixed=float(d.get("common_fixed", 0)),
    )


def load_cvp() -> CVPScenario | None:
    raw = _read_json(CVP_FILE, None)
    if raw is None:
        return None
    return _cvp_from_dict(raw)


def save_cvp(cvp: CVPScenario) -> None:
    from dataclasses import asdict
    _atomic_write(CVP_FILE, asdict(cvp))


def upsert_product(product: Product) -> None:
    items = load_products()
    for i, p in enumerate(items):
        if p.id == product.id:
            items[i] = product
            break
    else:
        items.append(product)
    save_products(items)


def delete_product(product_id: str) -> None:
    items = [p for p in load_products() if p.id != product_id]
    save_products(items)
    actuals = [a for a in load_actuals() if a.product_id != product_id]
    save_actuals(actuals)


def upsert_actual(actual: Actual) -> None:
    items = load_actuals()
    for i, a in enumerate(items):
        if a.product_id == actual.product_id and a.period == actual.period:
            items[i] = actual
            break
    else:
        items.append(actual)
    save_actuals(items)


def delete_actual(product_id: str, period: str) -> None:
    items = [a for a in load_actuals()
             if not (a.product_id == product_id and a.period == period)]
    save_actuals(items)


def get_product(product_id: str) -> Product | None:
    for p in load_products():
        if p.id == product_id:
            return p
    return None


def get_actual(product_id: str, period: str) -> Actual | None:
    for a in load_actuals():
        if a.product_id == product_id and a.period == period:
            return a
    return None
