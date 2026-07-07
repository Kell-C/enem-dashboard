(function (ED) {
  const { BL, CFG } = ED.Config;

  ED.createChart = function (id, traces, layout, config) {
    const container = document.getElementById(id);
    if (!container || typeof Plotly === 'undefined') return Promise.resolve(null);
    const cfg = config || CFG;
    const lay = { ...BL, ...layout, datarevision: Date.now() };
    if (container.data && container.data.length) {
      return Plotly.react(id, traces, lay, cfg);
    }
    return Plotly.newPlot(id, traces, lay, cfg);
  };

  ED.segmentDirectionArrows = function (xs, ys, opts) {
    if (!xs || xs.length < 2) return [];
    const color = opts?.color || 'rgba(10,77,140,.6)';
    const arrowsize = opts?.arrowsize ?? 0.55;
    const arrowwidth = opts?.arrowwidth ?? 1.2;
    const standoff = opts?.standoff ?? 2;
    const startstandoff = opts?.startstandoff ?? 2;
    const out = [];
    for (let i = 0; i < xs.length - 1; i += 1) {
      out.push({
        x: xs[i + 1],
        y: ys[i + 1],
        ax: xs[i],
        ay: ys[i],
        xref: 'x',
        yref: 'y',
        axref: 'x',
        ayref: 'y',
        showarrow: true,
        arrowhead: 2,
        arrowsize,
        arrowwidth,
        arrowcolor: color,
        standoff,
        startstandoff,
        text: '',
        captureevents: false,
      });
    }
    return out;
  };

  ED.segmentArrowsFromSeries = function (anos, vals, opts) {
    const xs = [];
    const ys = [];
    (anos || []).forEach((a, i) => {
      const v = vals[i];
      if (v != null && !Number.isNaN(v)) {
        xs.push(a);
        ys.push(v);
      }
    });
    return ED.segmentDirectionArrows(xs, ys, opts);
  };

  ED.spark = function (ctx, id, vals, col, inv) {
    const { ANOS } = ctx;
    const sparkCfg = { ...CFG, displayModeBar: false, staticPlot: true, responsive: false };
    const baseLayout = {
      ...BL,
      margin: { l: 2, r: 2, t: 4, b: 2 },
      height: 34,
      showlegend: false,
      xaxis: { visible: false },
      yaxis: { visible: false, autorange: inv ? 'reversed' : true },
    };
    const layout = ED.Config.mergePandemia
      ? ED.Config.mergePandemia(baseLayout, { anos: ANOS, annotate: false })
      : baseLayout;
    layout.annotations = ED.segmentArrowsFromSeries(ANOS, vals, {
      color: col,
      arrowsize: 0.42,
      arrowwidth: 1,
      standoff: 1.5,
      startstandoff: 1.5,
    });
    return Plotly.newPlot(id, [
      { x: ANOS, y: vals, mode: 'lines', line: { color: col, width: 2 }, hoverinfo: 'skip' },
    ], layout, sparkCfg);
  };

  ED.withPandemia = function (layout, opts) {
    return ED.Config.mergePandemia ? ED.Config.mergePandemia(layout, opts || {}) : layout;
  };

  ED.lazySection = function (idx, fn) {
    const el = document.querySelectorAll('.secacc')[idx];
    if (!el) return;
    const go = () => { if (el.dataset.lz) return; el.dataset.lz = '1'; fn(); };
    if (el.open) requestAnimationFrame(go);
    else el.addEventListener('toggle', () => { if (el.open) requestAnimationFrame(go); });
  };

  ED.lazyTabPanel = function (panelId, fn) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    const go = () => { if (panel.dataset.lz) return; panel.dataset.lz = '1'; fn(); };
    const tabBtn = document.querySelector(`[data-tab="${panelId}"]`);
    if (tabBtn) tabBtn.addEventListener('click', () => requestAnimationFrame(go));
    if (panel.classList.contains('is-active') && !panel.hidden) requestAnimationFrame(go);
    document.addEventListener('dash-tab-show', (e) => {
      if (e.detail && e.detail.id === panelId) requestAnimationFrame(go);
    });
  };

  ED.initDashTabs = function () {
    const root = document.getElementById('dashTabs');
    if (!root || root.dataset.ready) return;
    root.dataset.ready = '1';
    const tabs = root.querySelectorAll('.dash-tab');
    const panels = root.querySelectorAll('.dash-tabpanel');

    function showPanel(id) {
      tabs.forEach((tab) => {
        const on = tab.dataset.tab === id;
        tab.classList.toggle('is-active', on);
        tab.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      panels.forEach((panel) => {
        const on = panel.id === id;
        panel.classList.toggle('is-active', on);
        panel.hidden = !on;
      });
      document.dispatchEvent(new CustomEvent('dash-tab-show', { detail: { id } }));
      requestAnimationFrame(() => {
        const active = document.getElementById(id);
        if (!active || typeof Plotly === 'undefined') return;
        active.querySelectorAll('.js-plotly-plot').forEach((plot) => {
          if (plot.id) Plotly.Plots.resize(plot.id);
        });
      });
    }

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => showPanel(tab.dataset.tab));
    });

    const initial = root.querySelector('.dash-tab.is-active')?.dataset.tab
      || panels[0]?.id;
    if (initial) showPanel(initial);
  };

  ED.lazyDetails = function (selector, fn) {
    const el = document.querySelector(selector);
    if (!el) return;
    const go = () => { if (el.dataset.lz) return; el.dataset.lz = '1'; fn(); };
    if (el.open) requestAnimationFrame(go);
    else el.addEventListener('toggle', () => { if (el.open) requestAnimationFrame(go); });
  };
})(window.EnemDash);
