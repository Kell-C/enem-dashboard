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

  ED.spark = function (ctx, id, vals, col, inv) {
    const { ANOS } = ctx;
    const lastIdx = ANOS.length - 1;
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
    return Plotly.newPlot(id, [
      { x: ANOS, y: vals, mode: 'lines', line: { color: col, width: 2 }, hoverinfo: 'skip' },
      { x: [ANOS[lastIdx]], y: [vals[lastIdx]], mode: 'markers', marker: { color: col, size: 5 }, hoverinfo: 'skip' },
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
    if (panel.classList.contains('is-active')) requestAnimationFrame(go);
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
