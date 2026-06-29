/* 内部管理会計 — ブラウザ完結版
 * 計算ロジックは Python 版の core/variance.py, core/cvp.py に対応。
 * 永続化は localStorage を使用、JSON エクスポート / インポートにも対応。
 */
(function () {
  "use strict";

  // ---------- Storage ----------
  const LS_KEY = "internal-accounting/v1";

  const defaultState = () => ({ products: [], actuals: [], cvp: null });

  function loadState() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return defaultState();
      const s = JSON.parse(raw);
      return { products: s.products || [], actuals: s.actuals || [], cvp: s.cvp || null };
    } catch (e) {
      console.error("loadState error", e);
      return defaultState();
    }
  }

  function saveState() {
    localStorage.setItem(LS_KEY, JSON.stringify(state));
  }

  let state = loadState();

  // ---------- Formatting helpers ----------
  const yen = (v) => {
    const n = Number(v) || 0;
    return (n < 0 ? "-¥" : "¥") + Math.round(Math.abs(n)).toLocaleString();
  };
  const signedYen = (v) => {
    const n = Number(v) || 0;
    if (n > 0) return "+¥" + Math.round(n).toLocaleString();
    if (n < 0) return "-¥" + Math.round(-n).toLocaleString();
    return "¥0";
  };
  const pct = (v) => ((Number(v) || 0) * 100).toFixed(2) + "%";
  const signLabel = (v) => (v > 0 ? "不利" : v < 0 ? "有利" : "—");
  const signClass = (v) => (v > 0 ? "sign-unfav" : v < 0 ? "sign-fav" : "sign-zero");

  // ---------- Variance calculations (mirror of core/variance.py) ----------
  function stdQtyForOutput(stdQtyPerUnit, stdOutput, actualOutput) {
    if (!stdOutput || stdOutput <= 0) return 0;
    return (stdQtyPerUnit / stdOutput) * actualOutput;
  }

  function calcDetailed(product, actual) {
    const cc = product.cost_card || {};
    const lines = [];
    let totalActual = 0;
    let totalStandard = 0;

    const stdMats = cc.materials || [];
    const actMats = actual.materials || [];
    const matNames = Array.from(new Set([...stdMats.map((m) => m.name), ...actMats.map((m) => m.name)]));

    for (const name of matNames) {
      const std = stdMats.find((m) => m.name === name) || { std_price: 0, std_qty: 0 };
      const act = actMats.find((m) => m.name === name) || { actual_price: 0, actual_qty: 0 };
      const sq = stdQtyForOutput(std.std_qty, product.std_output, actual.actual_output);
      const priceVar = (act.actual_price - std.std_price) * act.actual_qty;
      const qtyVar = (act.actual_qty - sq) * std.std_price;
      lines.push({ name: `材料価格差異 (${name})`, value: priceVar, detail: `(実${act.actual_price} − 標${std.std_price}) × 実消費 ${act.actual_qty}` });
      lines.push({ name: `材料数量差異 (${name})`, value: qtyVar, detail: `(実${act.actual_qty} − 標${sq}) × 標単価 ${std.std_price}` });
      totalActual += act.actual_price * act.actual_qty;
      totalStandard += std.std_price * sq;
    }

    const stdLabs = cc.labors || [];
    const actLabs = actual.labors || [];
    const labNames = Array.from(new Set([...stdLabs.map((l) => l.process), ...actLabs.map((l) => l.process)]));
    let totActHours = 0;
    let totStdHours = 0;
    for (const name of labNames) {
      const std = stdLabs.find((l) => l.process === name) || { std_rate: 0, std_hours: 0 };
      const act = actLabs.find((l) => l.process === name) || { actual_rate: 0, actual_hours: 0 };
      const sh = stdQtyForOutput(std.std_hours, product.std_output, actual.actual_output);
      const rateVar = (act.actual_rate - std.std_rate) * act.actual_hours;
      const timeVar = (act.actual_hours - sh) * std.std_rate;
      lines.push({ name: `労務賃率差異 (${name})`, value: rateVar, detail: `(実${act.actual_rate} − 標${std.std_rate}) × 実時間 ${act.actual_hours}` });
      lines.push({ name: `労務時間差異 (${name})`, value: timeVar, detail: `(実${act.actual_hours} − 標${sh}) × 標賃率 ${std.std_rate}` });
      totalActual += act.actual_rate * act.actual_hours;
      totalStandard += std.std_rate * sh;
      totActHours += act.actual_hours;
      totStdHours += sh;
    }

    const oh = cc.overhead || {};
    const actOh = actual.overhead || {};
    const varBudget = (actOh.actual_variable || 0) - (oh.var_rate || 0) * totActHours;
    const varEff = (oh.var_rate || 0) * (totActHours - totStdHours);
    const fixedBudget = (actOh.actual_fixed || 0) - (oh.fixed_budget || 0);
    const stdFixedRate = oh.normal_hours ? (oh.fixed_budget || 0) / oh.normal_hours : 0;
    const fixedVolume = (oh.fixed_budget || 0) - stdFixedRate * totStdHours;
    lines.push({ name: "変動OH予算差異", value: varBudget, detail: `実${actOh.actual_variable || 0} − 標変動率${oh.var_rate || 0} × 実時間${totActHours}` });
    lines.push({ name: "変動OH能率差異", value: varEff, detail: `標変動率${oh.var_rate || 0} × (実時間${totActHours} − 標時間${totStdHours})` });
    lines.push({ name: "固定OH予算差異", value: fixedBudget, detail: `実${actOh.actual_fixed || 0} − 予算${oh.fixed_budget || 0}` });
    lines.push({ name: "固定OH操業度差異", value: fixedVolume, detail: `予算${oh.fixed_budget || 0} − 標固定率${stdFixedRate.toFixed(2)} × 標時間${totStdHours}` });
    totalActual += (actOh.actual_variable || 0) + (actOh.actual_fixed || 0);
    totalStandard += (oh.var_rate || 0) * totStdHours + stdFixedRate * totStdHours;

    return { product_id: product.id, period: actual.period, mode: "detailed", lines, total_actual: totalActual, total_standard: totalStandard, total_variance: totalActual - totalStandard };
  }

  function calcSimple(product, actual) {
    const sb = (product.cost_card && product.cost_card.simple_budget) || {};
    const sa = actual.simple || {};
    const lines = [];
    if (sb.material || sa.material) lines.push({ name: "材料費差異", value: (sa.material || 0) - (sb.material || 0), detail: `実${sa.material || 0} − 予算${sb.material || 0}` });
    if (sb.labor || sa.labor) lines.push({ name: "労務費差異", value: (sa.labor || 0) - (sb.labor || 0), detail: `実${sa.labor || 0} − 予算${sb.labor || 0}` });
    if (sb.overhead || sa.overhead) lines.push({ name: "経費差異", value: (sa.overhead || 0) - (sb.overhead || 0), detail: `実${sa.overhead || 0} − 予算${sb.overhead || 0}` });
    const actualTotal = sa.total || (sa.material || 0) + (sa.labor || 0) + (sa.overhead || 0);
    const budgetTotal = sb.total || (sb.material || 0) + (sb.labor || 0) + (sb.overhead || 0);
    lines.push({ name: "総差異", value: actualTotal - budgetTotal, detail: `実${actualTotal} − 予算${budgetTotal}` });
    return { product_id: product.id, period: actual.period, mode: "simple", lines, total_actual: actualTotal, total_standard: budgetTotal, total_variance: actualTotal - budgetTotal };
  }

  function calcVariance(product, actual) {
    return product.mode === "simple" ? calcSimple(product, actual) : calcDetailed(product, actual);
  }

  function unfavorableTotal(report) {
    if (report.mode === "simple") {
      const hasSplit = report.lines.some((l) => l.name !== "総差異");
      if (hasSplit) return report.lines.filter((l) => l.name !== "総差異" && l.value > 0).reduce((s, l) => s + l.value, 0);
      return report.lines.filter((l) => l.value > 0).reduce((s, l) => s + l.value, 0);
    }
    return report.lines.filter((l) => l.value > 0).reduce((s, l) => s + l.value, 0);
  }

  // ---------- CVP calculation ----------
  function calcCvp(sales, vc, fc, addFixed) {
    const cm = sales - vc;
    const cmRatio = sales ? cm / sales : 0;
    const bep = cmRatio > 0 ? fc / cmRatio : 0;
    const mos = sales - bep;
    const mosRatio = sales ? mos / sales : 0;
    const adjustedFixed = fc + addFixed;
    const adjustedBep = cmRatio > 0 ? adjustedFixed / cmRatio : 0;
    const shift = adjustedBep - bep;
    const adjustedMos = sales - adjustedBep;
    return { sales, variable_cost: vc, fixed_cost: fc, cm, cm_ratio: cmRatio, bep_sales: bep, margin_of_safety: mos, margin_of_safety_ratio: mosRatio, additional_fixed: addFixed, adjusted_fixed: adjustedFixed, adjusted_bep_sales: adjustedBep, bep_shift: shift, adjusted_margin_of_safety: adjustedMos };
  }

  // ---------- Generic helpers ----------
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }
  function uid() { return Math.random().toString(36).slice(2, 10); }
  function num(v) { const n = parseFloat(v); return isNaN(n) ? 0 : n; }

  // ---------- Tab switching ----------
  function showTab(name) {
    $$(".tab").forEach((el) => (el.hidden = el.id !== "tab-" + name));
    $$(".topnav a[data-tab]").forEach((a) => a.classList.toggle("active", a.dataset.tab === name));
    history.replaceState(null, "", "#" + name);
  }
  document.addEventListener("click", (e) => {
    const tabLink = e.target.closest("[data-tab]");
    if (tabLink) { e.preventDefault(); showTab(tabLink.dataset.tab); refresh(); return; }
    const goBtn = e.target.closest("[data-go]");
    if (goBtn) { showTab(goBtn.dataset.go); refresh(); }
  });

  // ---------- Dynamic row add/remove ----------
  const rowTemplates = {
    mat: ["品名", "標準/実際 単価", "標準/実際 数量"],
    lab: ["工程", "標準/実際 賃率", "標準/実際 時間"],
  };
  function makeRow(tpl, fieldPrefix, values) {
    const tr = document.createElement("tr");
    const names = tpl === "mat" ? ["mat_name", "mat_price", "mat_qty"] : ["lab_process", "lab_rate", "lab_hours"];
    const v = values || ["", "", ""];
    tr.innerHTML = `
      <td><input name="${names[0]}" value="${v[0] || ""}" /></td>
      <td><input name="${names[1]}" type="number" step="any" value="${v[1] || ""}" /></td>
      <td><input name="${names[2]}" type="number" step="any" value="${v[2] || ""}" /></td>
      <td><button type="button" class="btn ghost" data-remove-row>×</button></td>`;
    return tr;
  }
  document.addEventListener("click", (e) => {
    const addBtn = e.target.closest("[data-add-row]");
    if (addBtn) {
      const tbl = document.getElementById(addBtn.dataset.addRow);
      tbl.querySelector("tbody").appendChild(makeRow(addBtn.dataset.tpl));
      return;
    }
    const rmBtn = e.target.closest("[data-remove-row]");
    if (rmBtn) {
      const tr = rmBtn.closest("tr");
      const tbody = tr && tr.parentElement;
      if (tbody && tbody.children.length > 1) tr.remove();
      else if (tr) tr.querySelectorAll("input").forEach((i) => (i.value = ""));
    }
  });

  // ---------- Mode toggling on the product form ----------
  function applyMode(form) {
    const mode = form.elements["mode"].value;
    $$("section[data-mode]", form).forEach((s) => (s.hidden = s.dataset.mode !== mode));
  }

  // ---------- Render: dashboard ----------
  function renderDashboard() {
    const dp = $("#dashProducts");
    if (!state.products.length) {
      dp.innerHTML = `<p class="muted">まだ製品が登録されていません。</p>`;
    } else {
      dp.innerHTML = `<table class="grid"><thead><tr><th>製品名</th><th>モード</th><th>単位</th><th>標準生産量</th></tr></thead><tbody>${state.products.map((p) => `
        <tr><td>${escapeHtml(p.name)}</td><td><span class="badge mode-${p.mode}">${p.mode === "detailed" ? "詳細" : "簡易"}</span></td><td>${escapeHtml(p.unit || "")}</td><td>${p.std_output}</td></tr>
      `).join("")}</tbody></table>`;
    }

    const dv = $("#dashVariance");
    const summaries = [];
    for (const p of state.products) {
      const periods = state.actuals.filter((a) => a.product_id === p.id);
      if (!periods.length) continue;
      const latest = periods.slice().sort((a, b) => a.period.localeCompare(b.period)).pop();
      summaries.push({ p, report: calcVariance(p, latest) });
    }
    if (!summaries.length) {
      dv.innerHTML = `<p class="muted">実績がまだありません。</p>`;
    } else {
      dv.innerHTML = summaries.map(({ p, report }) => `
        <h3>${escapeHtml(p.name)} <small class="muted">(${escapeHtml(report.period)} · ${report.mode === "detailed" ? "詳細" : "簡易"})</small></h3>
        <table class="grid"><thead><tr><th>差異</th><th>金額</th><th>判定</th></tr></thead><tbody>
          ${report.lines.map((l) => `<tr><td>${escapeHtml(l.name)}</td><td class="right">${signedYen(l.value)}</td><td><span class="badge ${signClass(l.value)}">${signLabel(l.value)}</span></td></tr>`).join("")}
          <tr class="total"><td>総差異</td><td class="right">${signedYen(report.total_variance)}</td><td><span class="badge ${signClass(report.total_variance)}">${signLabel(report.total_variance)}</span></td></tr>
        </tbody></table>`).join("");
    }

    const dc = $("#dashCvp");
    if (state.cvp) {
      const unfav = computeUnfavTotalForCvp(state.cvp);
      const r = calcCvp(state.cvp.sales, state.cvp.variable_cost, state.cvp.fixed_cost, unfav);
      dc.innerHTML = `<ul class="kv">
        <li><span>売上高</span><b>${yen(r.sales)}</b></li>
        <li><span>限界利益率</span><b>${pct(r.cm_ratio)}</b></li>
        <li><span>BEP 売上高</span><b>${yen(r.bep_sales)}</b></li>
        <li><span>差異込み BEP</span><b>${yen(r.adjusted_bep_sales)}</b></li>
        <li><span>BEP シフト</span><b>${signedYen(r.bep_shift)}</b></li>
      </ul>`;
    } else {
      dc.innerHTML = `<p class="muted">CVP 入力がまだありません。</p>`;
    }
  }

  // ---------- Render: products tab ----------
  function renderProductList() {
    const el = $("#productList");
    if (!state.products.length) { el.innerHTML = `<p class="muted">まだ登録されていません。</p>`; return; }
    el.innerHTML = `<table class="grid"><thead><tr><th>製品名</th><th>モード</th><th>単位</th><th>標準生産量</th><th>材料</th><th>労務</th><th>操作</th></tr></thead><tbody>${state.products.map((p) => `
      <tr><td>${escapeHtml(p.name)}</td><td><span class="badge mode-${p.mode}">${p.mode === "detailed" ? "詳細" : "簡易"}</span></td><td>${escapeHtml(p.unit || "")}</td><td>${p.std_output}</td><td>${(p.cost_card.materials || []).length}</td><td>${(p.cost_card.labors || []).length}</td>
      <td>
        <button class="btn ghost" type="button" data-edit-product="${p.id}">編集</button>
        <button class="btn danger" type="button" data-delete-product="${p.id}">削除</button>
      </td></tr>`).join("")}</tbody></table>`;
  }

  function loadProductIntoForm(p) {
    const form = $("#productForm");
    form.elements["id"].value = p ? p.id : "";
    form.elements["name"].value = p ? p.name : "";
    form.elements["unit"].value = p ? p.unit || "個" : "個";
    form.elements["std_output"].value = p ? p.std_output : 1;
    form.elements["mode"].value = p ? p.mode : "detailed";
    $("#matTable tbody").innerHTML = "";
    $("#labTable tbody").innerHTML = "";
    if (p) {
      for (const m of p.cost_card.materials || []) $("#matTable tbody").appendChild(makeRow("mat", null, [m.name, m.std_price, m.std_qty]));
      for (const l of p.cost_card.labors || []) $("#labTable tbody").appendChild(makeRow("lab", null, [l.process, l.std_rate, l.std_hours]));
    }
    if (!$("#matTable tbody").children.length) $("#matTable tbody").appendChild(makeRow("mat"));
    if (!$("#labTable tbody").children.length) $("#labTable tbody").appendChild(makeRow("lab"));
    const oh = (p && p.cost_card.overhead) || {};
    form.elements["oh_var_rate"].value = oh.var_rate || "";
    form.elements["oh_fixed_budget"].value = oh.fixed_budget || "";
    form.elements["oh_normal_hours"].value = oh.normal_hours || "";
    const sb = (p && p.cost_card.simple_budget) || {};
    form.elements["simple_total"].value = sb.total || "";
    form.elements["simple_material"].value = sb.material || "";
    form.elements["simple_labor"].value = sb.labor || "";
    form.elements["simple_overhead"].value = sb.overhead || "";
    $("#productEditTitle").textContent = p ? "製品編集: " + p.name : "新規製品";
    applyMode(form);
  }

  function readProductForm() {
    const form = $("#productForm");
    const id = form.elements["id"].value || uid();
    const mats = [];
    $$("#matTable tbody tr").forEach((tr) => {
      const name = $("input[name=mat_name]", tr).value.trim();
      if (!name) return;
      mats.push({ name, std_price: num($("input[name=mat_price]", tr).value), std_qty: num($("input[name=mat_qty]", tr).value) });
    });
    const labs = [];
    $$("#labTable tbody tr").forEach((tr) => {
      const process = $("input[name=lab_process]", tr).value.trim();
      if (!process) return;
      labs.push({ process, std_rate: num($("input[name=lab_rate]", tr).value), std_hours: num($("input[name=lab_hours]", tr).value) });
    });
    return {
      id,
      name: form.elements["name"].value.trim() || id,
      mode: form.elements["mode"].value,
      unit: form.elements["unit"].value || "個",
      std_output: num(form.elements["std_output"].value) || 1,
      cost_card: {
        materials: mats,
        labors: labs,
        overhead: { var_rate: num(form.elements["oh_var_rate"].value), fixed_budget: num(form.elements["oh_fixed_budget"].value), normal_hours: num(form.elements["oh_normal_hours"].value) },
        simple_budget: { total: num(form.elements["simple_total"].value), material: num(form.elements["simple_material"].value), labor: num(form.elements["simple_labor"].value), overhead: num(form.elements["simple_overhead"].value) },
      },
    };
  }

  // ---------- Render: actuals tab ----------
  function renderActualProductOptions() {
    const sel = $("#actualProductSelect");
    sel.innerHTML = state.products.map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${p.mode === "detailed" ? "詳細" : "簡易"})</option>`).join("");
  }

  function loadActualFormForProduct(productId, existing) {
    const product = state.products.find((p) => p.id === productId);
    if (!product) return;
    const form = $("#actualForm");
    form.elements["product_id"].value = product.id;
    form.elements["period"].value = existing ? existing.period : "2026-Q1";
    form.elements["actual_output"].value = existing ? existing.actual_output : 1;
    $("#actualDetailedSection").hidden = product.mode !== "detailed";
    $("#actualSimpleSection").hidden = product.mode !== "simple";

    $("#actMatTable tbody").innerHTML = "";
    $("#actLabTable tbody").innerHTML = "";
    if (product.mode === "detailed") {
      for (const m of product.cost_card.materials || []) {
        const act = existing && existing.materials ? existing.materials.find((x) => x.name === m.name) : null;
        $("#actMatTable tbody").appendChild(makeRow("mat", null, [m.name, act ? act.actual_price : "", act ? act.actual_qty : ""]));
      }
      for (const l of product.cost_card.labors || []) {
        const act = existing && existing.labors ? existing.labors.find((x) => x.process === l.process) : null;
        $("#actLabTable tbody").appendChild(makeRow("lab", null, [l.process, act ? act.actual_rate : "", act ? act.actual_hours : ""]));
      }
      if (!$("#actMatTable tbody").children.length) $("#actMatTable tbody").appendChild(makeRow("mat"));
      if (!$("#actLabTable tbody").children.length) $("#actLabTable tbody").appendChild(makeRow("lab"));
      const oh = (existing && existing.overhead) || {};
      form.elements["oh_var"].value = oh.actual_variable || "";
      form.elements["oh_fixed"].value = oh.actual_fixed || "";
    } else {
      const s = (existing && existing.simple) || {};
      form.elements["simple_total"].value = s.total || "";
      form.elements["simple_material"].value = s.material || "";
      form.elements["simple_labor"].value = s.labor || "";
      form.elements["simple_overhead"].value = s.overhead || "";
    }
  }

  function readActualForm() {
    const form = $("#actualForm");
    const product = state.products.find((p) => p.id === form.elements["product_id"].value);
    if (!product) return null;
    const a = { product_id: product.id, period: form.elements["period"].value.trim(), actual_output: num(form.elements["actual_output"].value) || 1, materials: [], labors: [], overhead: {}, simple: {} };
    if (product.mode === "detailed") {
      $$("#actMatTable tbody tr").forEach((tr) => {
        const name = $("input[name=mat_name]", tr).value.trim();
        if (!name) return;
        a.materials.push({ name, actual_price: num($("input[name=mat_price]", tr).value), actual_qty: num($("input[name=mat_qty]", tr).value) });
      });
      $$("#actLabTable tbody tr").forEach((tr) => {
        const process = $("input[name=lab_process]", tr).value.trim();
        if (!process) return;
        a.labors.push({ process, actual_rate: num($("input[name=lab_rate]", tr).value), actual_hours: num($("input[name=lab_hours]", tr).value) });
      });
      a.overhead = { actual_variable: num(form.elements["oh_var"].value), actual_fixed: num(form.elements["oh_fixed"].value) };
    } else {
      a.simple = { total: num(form.elements["simple_total"].value), material: num(form.elements["simple_material"].value), labor: num(form.elements["simple_labor"].value), overhead: num(form.elements["simple_overhead"].value) };
    }
    return a;
  }

  function renderActualList() {
    const el = $("#actualList");
    if (!state.actuals.length) { el.innerHTML = `<p class="muted">まだ実績がありません。</p>`; return; }
    el.innerHTML = `<table class="grid"><thead><tr><th>製品</th><th>期間</th><th>実生産量</th><th>操作</th></tr></thead><tbody>${state.actuals.map((a) => {
      const p = state.products.find((x) => x.id === a.product_id);
      return `<tr><td>${escapeHtml(p ? p.name : a.product_id)}</td><td>${escapeHtml(a.period)}</td><td>${a.actual_output}</td>
        <td>
          <button class="btn ghost" type="button" data-show-variance='${JSON.stringify({ pid: a.product_id, period: a.period })}'>差異分析</button>
          <button class="btn ghost" type="button" data-edit-actual='${JSON.stringify({ pid: a.product_id, period: a.period })}'>編集</button>
          <button class="btn danger" type="button" data-delete-actual='${JSON.stringify({ pid: a.product_id, period: a.period })}'>削除</button>
        </td></tr>`;
    }).join("")}</tbody></table>`;
  }

  let varChartInstance = null;
  function showVariance(productId, period) {
    const product = state.products.find((p) => p.id === productId);
    const actual = state.actuals.find((a) => a.product_id === productId && a.period === period);
    if (!product || !actual) return;
    const report = calcVariance(product, actual);
    const card = $("#varianceCard");
    card.hidden = false;
    $("#varianceContent").innerHTML = `
      <ul class="kv kv-grid">
        <li><span>原価モード</span><b>${report.mode === "detailed" ? "詳細" : "簡易"}</b></li>
        <li><span>実生産量</span><b>${actual.actual_output} ${escapeHtml(product.unit || "")}</b></li>
        <li><span>実際総原価</span><b>${yen(report.total_actual)}</b></li>
        <li><span>標準/予算</span><b>${yen(report.total_standard)}</b></li>
        <li><span>総差異</span><b><span class="badge ${signClass(report.total_variance)}">${signLabel(report.total_variance)}</span> ${signedYen(report.total_variance)}</b></li>
      </ul>
      <h3>差異明細</h3>
      <table class="grid"><thead><tr><th>差異</th><th>計算式</th><th>金額</th><th>判定</th></tr></thead><tbody>
        ${report.lines.map((l) => `<tr><td>${escapeHtml(l.name)}</td><td class="muted small">${escapeHtml(l.detail)}</td><td class="right">${signedYen(l.value)}</td><td><span class="badge ${signClass(l.value)}">${signLabel(l.value)}</span></td></tr>`).join("")}
      </tbody></table>`;
    if (varChartInstance) varChartInstance.destroy();
    varChartInstance = new Chart($("#varChart"), {
      type: "bar",
      data: {
        labels: report.lines.map((l) => l.name),
        datasets: [{ label: "差異（＋ = 不利、− = 有利）", data: report.lines.map((l) => l.value), backgroundColor: report.lines.map((l) => l.value > 0 ? "rgba(185,28,28,.75)" : l.value < 0 ? "rgba(4,120,87,.75)" : "rgba(107,114,128,.5)") }],
      },
      options: { indexAxis: "y", responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => "¥" + Number(ctx.raw).toLocaleString() } } }, scales: { x: { ticks: { callback: (v) => "¥" + v.toLocaleString() } } } },
    });
    card.scrollIntoView({ behavior: "smooth" });
  }

  // ---------- CVP rendering ----------
  function computeUnfavTotalForCvp(cvp) {
    if (!cvp || !cvp.include_variance_product_ids) return 0;
    let total = 0;
    for (const pid of cvp.include_variance_product_ids) {
      const product = state.products.find((p) => p.id === pid);
      if (!product) continue;
      let target = state.actuals.filter((a) => a.product_id === pid);
      if (cvp.include_variance_period) target = target.filter((a) => a.period === cvp.include_variance_period);
      if (!target.length) continue;
      const latest = target.slice().sort((a, b) => a.period.localeCompare(b.period)).pop();
      total += unfavorableTotal(calcVariance(product, latest));
    }
    return total;
  }

  let cvpChartInstance = null;
  function renderCvp() {
    const form = $("#cvpForm");
    const cvp = state.cvp || { sales: 0, variable_cost: 0, fixed_cost: 0, include_variance_product_ids: [], include_variance_period: "" };
    form.elements["sales"].value = cvp.sales || "";
    form.elements["variable_cost"].value = cvp.variable_cost || "";
    form.elements["fixed_cost"].value = cvp.fixed_cost || "";
    const periods = Array.from(new Set(state.actuals.map((a) => a.period))).sort();
    $("#cvpPeriodSelect").innerHTML = `<option value="">直近の期間</option>` + periods.map((p) => `<option value="${escapeHtml(p)}" ${cvp.include_variance_period === p ? "selected" : ""}>${escapeHtml(p)}</option>`).join("");
    $("#cvpProductCheckboxes").innerHTML = state.products.map((p) => `
      <label class="checkbox"><input type="checkbox" name="include_pid" value="${p.id}" ${(cvp.include_variance_product_ids || []).includes(p.id) ? "checked" : ""} /> ${escapeHtml(p.name)} <span class="muted small">(${p.mode === "detailed" ? "詳細" : "簡易"})</span></label>`).join("");

    const unfavTotal = computeUnfavTotalForCvp(cvp);
    const r = calcCvp(num(cvp.sales), num(cvp.variable_cost), num(cvp.fixed_cost), unfavTotal);
    const breakdown = [];
    for (const pid of cvp.include_variance_product_ids || []) {
      const product = state.products.find((p) => p.id === pid);
      if (!product) continue;
      let target = state.actuals.filter((a) => a.product_id === pid);
      if (cvp.include_variance_period) target = target.filter((a) => a.period === cvp.include_variance_period);
      if (!target.length) continue;
      const latest = target.slice().sort((a, b) => a.period.localeCompare(b.period)).pop();
      breakdown.push({ product, period: latest.period, value: unfavorableTotal(calcVariance(product, latest)) });
    }

    $("#cvpResult").innerHTML = `
      <ul class="kv kv-grid">
        <li><span>売上高</span><b>${yen(r.sales)}</b></li>
        <li><span>変動費</span><b>${yen(r.variable_cost)}</b></li>
        <li><span>固定費</span><b>${yen(r.fixed_cost)}</b></li>
        <li><span>限界利益</span><b>${yen(r.cm)}</b></li>
        <li><span>限界利益率</span><b>${pct(r.cm_ratio)}</b></li>
        <li><span>BEP 売上高</span><b>${yen(r.bep_sales)}</b></li>
        <li><span>安全余裕額</span><b>${yen(r.margin_of_safety)}</b></li>
        <li><span>安全余裕率</span><b>${pct(r.margin_of_safety_ratio)}</b></li>
      </ul>
      <h3>差異込みの BEP 比較</h3>
      <ul class="kv kv-grid">
        <li><span>不利差異の合計</span><b>${yen(unfavTotal)}</b></li>
        <li><span>調整後固定費</span><b>${yen(r.adjusted_fixed)}</b></li>
        <li><span>調整後 BEP 売上高</span><b>${yen(r.adjusted_bep_sales)}</b></li>
        <li><span>BEP シフト幅</span><b>${signedYen(r.bep_shift)}</b></li>
        <li><span>調整後 安全余裕額</span><b>${yen(r.adjusted_margin_of_safety)}</b></li>
      </ul>
      ${breakdown.length ? `<h4>差異内訳</h4><table class="grid"><thead><tr><th>製品</th><th>期間</th><th>不利差異合計</th></tr></thead><tbody>${breakdown.map((b) => `<tr><td>${escapeHtml(b.product.name)}</td><td>${escapeHtml(b.period)}</td><td class="right">${yen(b.value)}</td></tr>`).join("")}</tbody></table>` : ""}
    `;
    if (cvpChartInstance) cvpChartInstance.destroy();
    const maxSales = Math.max(r.sales, r.bep_sales, r.adjusted_bep_sales) * 1.25 || 100;
    const points = 12;
    const xs = Array.from({ length: points + 1 }, (_, i) => (maxSales * i) / points);
    cvpChartInstance = new Chart($("#cvpChart"), {
      type: "line",
      data: {
        labels: xs.map((x) => Math.round(x).toLocaleString()),
        datasets: [
          { label: "売上線", data: xs, borderColor: "#2563eb", backgroundColor: "transparent", pointRadius: 0 },
          { label: "変動費線", data: xs.map((x) => x * (1 - r.cm_ratio)), borderColor: "#9ca3af", borderDash: [4, 4], backgroundColor: "transparent", pointRadius: 0 },
          { label: "総費用（元）", data: xs.map((x) => x * (1 - r.cm_ratio) + r.fixed_cost), borderColor: "#dc2626", backgroundColor: "transparent", pointRadius: 0 },
          { label: "総費用（差異込み）", data: xs.map((x) => x * (1 - r.cm_ratio) + r.adjusted_fixed), borderColor: "#b45309", borderDash: [6, 4], backgroundColor: "transparent", pointRadius: 0 },
        ],
      },
      options: { responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ": ¥" + Math.round(ctx.raw).toLocaleString() } } }, scales: { x: { title: { display: true, text: "売上高（¥）" } }, y: { title: { display: true, text: "金額（¥）" }, ticks: { callback: (v) => "¥" + Number(v).toLocaleString() } } } },
    });
  }

  // ---------- Event wiring ----------
  $("#productForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const p = readProductForm();
    const i = state.products.findIndex((x) => x.id === p.id);
    if (i >= 0) state.products[i] = p; else state.products.push(p);
    saveState(); refresh();
    loadProductIntoForm(null);
  });
  $("#productForm").addEventListener("change", (e) => {
    if (e.target.name === "mode") applyMode($("#productForm"));
  });
  $("#productReset").addEventListener("click", (e) => { e.preventDefault(); loadProductIntoForm(null); });

  document.addEventListener("click", (e) => {
    const editBtn = e.target.closest("[data-edit-product]");
    if (editBtn) { const p = state.products.find((x) => x.id === editBtn.dataset.editProduct); if (p) { loadProductIntoForm(p); window.scrollTo({ top: 0, behavior: "smooth" }); } return; }
    const delBtn = e.target.closest("[data-delete-product]");
    if (delBtn) {
      if (!confirm("製品を削除します。関連実績も削除されます。よろしいですか?")) return;
      state.products = state.products.filter((x) => x.id !== delBtn.dataset.deleteProduct);
      state.actuals = state.actuals.filter((a) => a.product_id !== delBtn.dataset.deleteProduct);
      saveState(); refresh();
      return;
    }
    const showVarBtn = e.target.closest("[data-show-variance]");
    if (showVarBtn) { const o = JSON.parse(showVarBtn.dataset.showVariance); showVariance(o.pid, o.period); return; }
    const editActBtn = e.target.closest("[data-edit-actual]");
    if (editActBtn) { const o = JSON.parse(editActBtn.dataset.editActual); const existing = state.actuals.find((a) => a.product_id === o.pid && a.period === o.period); $("#actualProductSelect").value = o.pid; loadActualFormForProduct(o.pid, existing); window.scrollTo({ top: 0, behavior: "smooth" }); return; }
    const delActBtn = e.target.closest("[data-delete-actual]");
    if (delActBtn) {
      if (!confirm("実績を削除します。よろしいですか?")) return;
      const o = JSON.parse(delActBtn.dataset.deleteActual);
      state.actuals = state.actuals.filter((a) => !(a.product_id === o.pid && a.period === o.period));
      saveState(); refresh();
    }
  });

  $("#actualProductSelect").addEventListener("change", () => loadActualFormForProduct($("#actualProductSelect").value, null));
  $("#actualForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const a = readActualForm();
    if (!a) return;
    const i = state.actuals.findIndex((x) => x.product_id === a.product_id && x.period === a.period);
    if (i >= 0) state.actuals[i] = a; else state.actuals.push(a);
    saveState(); refresh();
    showVariance(a.product_id, a.period);
  });

  $("#cvpForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const form = $("#cvpForm");
    state.cvp = {
      sales: num(form.elements["sales"].value),
      variable_cost: num(form.elements["variable_cost"].value),
      fixed_cost: num(form.elements["fixed_cost"].value),
      include_variance_product_ids: $$("input[name=include_pid]:checked", form).map((i) => i.value),
      include_variance_period: form.elements["include_period"].value,
    };
    saveState(); renderCvp(); renderDashboard();
  });

  // Export / import / reset
  $("#btnExport").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "internal-accounting-" + new Date().toISOString().slice(0, 10) + ".json"; a.click();
    URL.revokeObjectURL(url);
  });
  $("#fileImport").addEventListener("change", (e) => {
    const file = e.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const s = JSON.parse(reader.result);
        state = { products: s.products || [], actuals: s.actuals || [], cvp: s.cvp || null };
        saveState(); refresh();
        alert("インポート完了");
      } catch (err) { alert("JSON 読み込みエラー: " + err); }
    };
    reader.readAsText(file);
    e.target.value = "";
  });
  $("#btnReset").addEventListener("click", () => {
    if (!confirm("全データを削除します。よろしいですか?")) return;
    state = defaultState();
    saveState(); refresh();
  });

  // ---------- Top-level refresh / boot ----------
  function refresh() {
    renderDashboard();
    renderProductList();
    renderActualProductOptions();
    if ($("#actualProductSelect").value) {
      loadActualFormForProduct($("#actualProductSelect").value, null);
    } else if (state.products.length) {
      $("#actualProductSelect").value = state.products[0].id;
      loadActualFormForProduct(state.products[0].id, null);
    }
    renderActualList();
    renderCvp();
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function boot() {
    loadProductIntoForm(null);
    refresh();
    const hashTab = (location.hash || "").replace(/^#/, "");
    if (["dashboard", "products", "actuals", "cvp"].includes(hashTab)) showTab(hashTab);
    else showTab("dashboard");
  }

  boot();
})();
