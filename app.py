"""Flask front-end for the internal management-accounting tool.

Run:
    python app.py
Then open http://127.0.0.1:7862
"""
from __future__ import annotations

import uuid
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

from core import cvp as cvp_mod
from core import reports as rpt
from core import storage
from core import variance as var_mod
from core.models import (
    Actual,
    BOMItem,
    CVPInput,
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


app = Flask(__name__, static_folder="static", template_folder="templates")
HERE = Path(__file__).resolve().parent


def _float(form, key: str, default: float = 0.0) -> float:
    raw = form.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@app.template_filter("yen")
def filter_yen(v):
    try:
        return rpt.yen(float(v))
    except (TypeError, ValueError):
        return v


@app.route("/")
def index():
    products = storage.load_products()
    actuals = storage.load_actuals()
    cvp_input = storage.load_cvp()

    latest_variance = []
    for product in products:
        product_actuals = [a for a in actuals if a.product_id == product.id]
        if not product_actuals:
            continue
        latest = sorted(product_actuals, key=lambda a: a.period)[-1]
        report = var_mod.calc(product, latest)
        latest_variance.append({
            "product": product,
            "view": rpt.variance_to_view(report),
        })

    cvp_view = None
    if cvp_input:
        unfav = 0.0
        if cvp_input.include_variance_product_ids:
            for product in products:
                if product.id not in cvp_input.include_variance_product_ids:
                    continue
                target = [a for a in actuals if a.product_id == product.id]
                if cvp_input.include_variance_period:
                    target = [a for a in target if a.period == cvp_input.include_variance_period]
                if not target:
                    continue
                latest = sorted(target, key=lambda a: a.period)[-1]
                unfav += var_mod.unfavorable_total(var_mod.calc(product, latest))
        result = cvp_mod.calc(
            sales=cvp_input.sales,
            variable_cost=cvp_input.variable_cost,
            fixed_cost=cvp_input.fixed_cost,
            additional_fixed=unfav,
        )
        cvp_view = rpt.cvp_to_view(result)

    return render_template(
        "index.html",
        products=products,
        actuals=actuals,
        latest_variance=latest_variance,
        cvp_view=cvp_view,
    )


@app.route("/products")
def product_list():
    products = storage.load_products()
    return render_template("products.html", products=products, editing=None)


@app.route("/products/new", methods=["GET", "POST"])
def product_new():
    if request.method == "POST":
        product = _product_from_form(request.form, new=True)
        storage.upsert_product(product)
        return redirect(url_for("product_list"))
    blank = Product(id="", name="")
    return render_template("product_edit.html", product=blank, new=True)


@app.route("/products/<pid>/edit", methods=["GET", "POST"])
def product_edit(pid: str):
    existing = storage.get_product(pid)
    if not existing:
        abort(404)
    if request.method == "POST":
        product = _product_from_form(request.form, new=False, pid=pid)
        storage.upsert_product(product)
        return redirect(url_for("product_list"))
    return render_template("product_edit.html", product=existing, new=False)


@app.route("/products/<pid>/delete", methods=["POST"])
def product_delete(pid: str):
    storage.delete_product(pid)
    return redirect(url_for("product_list"))


def _product_from_form(form, *, new: bool, pid: str | None = None) -> Product:
    pid = pid or form.get("id") or str(uuid.uuid4())[:8]
    mode = form.get("mode", "detailed")

    materials: list[BOMItem] = []
    names = form.getlist("mat_name")
    prices = form.getlist("mat_price")
    qtys = form.getlist("mat_qty")
    for n, p, q in zip(names, prices, qtys):
        if not n.strip():
            continue
        materials.append(BOMItem(name=n.strip(), std_price=_float({"x": p}, "x"), std_qty=_float({"x": q}, "x")))

    labors: list[LaborStd] = []
    lnames = form.getlist("lab_process")
    lrates = form.getlist("lab_rate")
    lhours = form.getlist("lab_hours")
    for n, r, h in zip(lnames, lrates, lhours):
        if not n.strip():
            continue
        labors.append(LaborStd(process=n.strip(), std_rate=_float({"x": r}, "x"), std_hours=_float({"x": h}, "x")))

    overhead = OHStd(
        var_rate=_float(form, "oh_var_rate"),
        fixed_budget=_float(form, "oh_fixed_budget"),
        normal_hours=_float(form, "oh_normal_hours"),
    )
    simple = SimpleBudget(
        total=_float(form, "simple_total"),
        material=_float(form, "simple_material"),
        labor=_float(form, "simple_labor"),
        overhead=_float(form, "simple_overhead"),
    )

    return Product(
        id=pid,
        name=form.get("name", "").strip() or pid,
        mode=mode if mode in ("detailed", "simple") else "detailed",
        unit=form.get("unit", "個"),
        std_output=_float(form, "std_output", 1.0) or 1.0,
        cost_card=CostCard(materials=materials, labors=labors, overhead=overhead, simple_budget=simple),
    )


@app.route("/actuals")
def actuals_list():
    products = storage.load_products()
    actuals = storage.load_actuals()
    return render_template("actuals.html", products=products, actuals=actuals)


@app.route("/actuals/edit", methods=["GET", "POST"])
def actuals_edit():
    product_id = request.args.get("product_id") or request.form.get("product_id", "")
    period = request.args.get("period") or request.form.get("period", "")

    if request.method == "POST":
        actual = _actual_from_form(request.form)
        storage.upsert_actual(actual)
        return redirect(url_for("variance_view", product_id=actual.product_id, period=actual.period))

    products = storage.load_products()
    if not products:
        return redirect(url_for("product_list"))
    if not product_id:
        product_id = products[0].id
    product = storage.get_product(product_id)
    if not product:
        abort(404)
    existing = storage.get_actual(product_id, period) if period else None
    blank = existing or Actual(product_id=product_id, period=period or "2026-Q1")
    return render_template("actual_edit.html", product=product, products=products, actual=blank)


@app.route("/actuals/delete", methods=["POST"])
def actuals_delete():
    storage.delete_actual(request.form["product_id"], request.form["period"])
    return redirect(url_for("actuals_list"))


def _actual_from_form(form) -> Actual:
    materials: list[MaterialActual] = []
    names = form.getlist("mat_name")
    prices = form.getlist("mat_price")
    qtys = form.getlist("mat_qty")
    for n, p, q in zip(names, prices, qtys):
        if not n.strip():
            continue
        materials.append(MaterialActual(name=n.strip(), actual_price=_float({"x": p}, "x"), actual_qty=_float({"x": q}, "x")))

    labors: list[LaborActual] = []
    lnames = form.getlist("lab_process")
    lrates = form.getlist("lab_rate")
    lhours = form.getlist("lab_hours")
    for n, r, h in zip(lnames, lrates, lhours):
        if not n.strip():
            continue
        labors.append(LaborActual(process=n.strip(), actual_rate=_float({"x": r}, "x"), actual_hours=_float({"x": h}, "x")))

    return Actual(
        product_id=form["product_id"],
        period=form["period"].strip(),
        actual_output=_float(form, "actual_output", 1.0) or 1.0,
        materials=materials,
        labors=labors,
        overhead=OHActual(
            actual_variable=_float(form, "oh_var"),
            actual_fixed=_float(form, "oh_fixed"),
        ),
        simple=SimpleActual(
            total=_float(form, "simple_total"),
            material=_float(form, "simple_material"),
            labor=_float(form, "simple_labor"),
            overhead=_float(form, "simple_overhead"),
        ),
    )


@app.route("/variance/<product_id>/<period>")
def variance_view(product_id: str, period: str):
    product = storage.get_product(product_id)
    actual = storage.get_actual(product_id, period)
    if not product or not actual:
        abort(404)
    report = var_mod.calc(product, actual)
    view = rpt.variance_to_view(report)
    return render_template("variance.html", product=product, actual=actual, view=view)


@app.route("/cvp", methods=["GET", "POST"])
def cvp_view():
    products = storage.load_products()
    if request.method == "POST":
        cvp_input = CVPInput(
            sales=_float(request.form, "sales"),
            variable_cost=_float(request.form, "variable_cost"),
            fixed_cost=_float(request.form, "fixed_cost"),
            include_variance_product_ids=request.form.getlist("include_pid"),
            include_variance_period=request.form.get("include_period", "").strip(),
        )
        storage.save_cvp(cvp_input)
        return redirect(url_for("cvp_view"))

    cvp_input = storage.load_cvp() or CVPInput(sales=0, variable_cost=0, fixed_cost=0)
    actuals = storage.load_actuals()

    unfav_breakdown: list[dict] = []
    unfav_total = 0.0
    for product in products:
        if product.id not in cvp_input.include_variance_product_ids:
            continue
        target = [a for a in actuals if a.product_id == product.id]
        if cvp_input.include_variance_period:
            target = [a for a in target if a.period == cvp_input.include_variance_period]
        if not target:
            continue
        latest = sorted(target, key=lambda a: a.period)[-1]
        report = var_mod.calc(product, latest)
        u = var_mod.unfavorable_total(report)
        unfav_total += u
        unfav_breakdown.append({
            "product": product,
            "period": latest.period,
            "unfav_total": rpt.signed_yen(u),
            "unfav_value": u,
        })

    result = cvp_mod.calc(
        sales=cvp_input.sales,
        variable_cost=cvp_input.variable_cost,
        fixed_cost=cvp_input.fixed_cost,
        additional_fixed=unfav_total,
    )
    cvp_result_view = rpt.cvp_to_view(result)

    periods = sorted({a.period for a in actuals})

    return render_template(
        "cvp.html",
        cvp_input=cvp_input,
        result=cvp_result_view,
        products=products,
        periods=periods,
        unfav_breakdown=unfav_breakdown,
        unfav_total=rpt.yen(unfav_total),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7862, debug=False)
