(function () {
  function cloneLastRow(tableId) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    const rows = tbody.querySelectorAll('tr');
    if (!rows.length) return;
    const clone = rows[rows.length - 1].cloneNode(true);
    clone.querySelectorAll('input').forEach((inp) => (inp.value = ''));
    clone.querySelectorAll('select').forEach((s) => (s.selectedIndex = 0));
    tbody.appendChild(clone);
  }

  document.addEventListener('click', (e) => {
    const addBtn = e.target.closest('[data-add-row]');
    if (addBtn) {
      cloneLastRow(addBtn.dataset.addRow);
      return;
    }
    const removeBtn = e.target.closest('[data-remove-row]');
    if (removeBtn) {
      const tr = removeBtn.closest('tr');
      const tbody = tr && tr.parentElement;
      if (tbody && tbody.querySelectorAll('tr').length > 1) {
        tr.remove();
      } else if (tr) {
        tr.querySelectorAll('input').forEach((inp) => (inp.value = ''));
      }
    }
  });

  const modeSelect = document.getElementById('modeSelect');
  function applyMode() {
    if (!modeSelect) return;
    const mode = modeSelect.value;
    document.querySelectorAll('[data-mode]').forEach((sec) => {
      sec.hidden = sec.dataset.mode !== mode;
    });
  }
  if (modeSelect) {
    modeSelect.addEventListener('change', applyMode);
    applyMode();
  }

  if (window.__variance && document.getElementById('varChart')) {
    const labels = window.__variance.map((r) => r.name);
    const values = window.__variance.map((r) => r.value);
    const colors = values.map((v) =>
      v > 0 ? 'rgba(185, 28, 28, 0.75)' : v < 0 ? 'rgba(4, 120, 87, 0.75)' : 'rgba(107, 114, 128, 0.5)'
    );
    new Chart(document.getElementById('varChart'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: '差異（＋ = 不利、− = 有利）',
            data: values,
            backgroundColor: colors,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        scales: { x: { ticks: { callback: (v) => '¥' + v.toLocaleString() } } },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => '¥' + Number(ctx.raw).toLocaleString(),
            },
          },
        },
      },
    });
  }

  if (window.__cvp && document.getElementById('cvpChart')) {
    const c = window.__cvp;
    const maxSales = Math.max(c.sales || 0, c.bep_sales || 0) * 1.25 || 100;
    const points = 12;
    const xs = Array.from({ length: points + 1 }, (_, i) => (maxSales * i) / points);
    const vcLine = xs.map((x) => x * (1 - c.cm_ratio));
    const totalCost = xs.map((x) => x * (1 - c.cm_ratio) + c.fixed_cost);
    const salesLine = xs.map((x) => x);

    new Chart(document.getElementById('cvpChart'), {
      type: 'line',
      data: {
        labels: xs.map((x) => Math.round(x).toLocaleString()),
        datasets: [
          { label: '売上線', data: salesLine, borderColor: '#2563eb', backgroundColor: 'transparent', tension: 0, pointRadius: 0 },
          { label: '変動費線', data: vcLine, borderColor: '#9ca3af', borderDash: [4, 4], backgroundColor: 'transparent', pointRadius: 0 },
          { label: '総費用線', data: totalCost, borderColor: '#dc2626', backgroundColor: 'transparent', pointRadius: 0 },
        ],
      },
      options: {
        responsive: true,
        scales: {
          x: { title: { display: true, text: '売上高（¥）' } },
          y: { title: { display: true, text: '金額（¥）' }, ticks: { callback: (v) => '¥' + Number(v).toLocaleString() } },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => ctx.dataset.label + ': ¥' + Math.round(ctx.raw).toLocaleString(),
            },
          },
        },
      },
    });
  }
})();
