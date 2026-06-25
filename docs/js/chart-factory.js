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
    return Plotly.newPlot(id, [
      { x: ANOS, y: vals, mode: 'lines', line: { color: col, width: 2 }, hoverinfo: 'skip' },
      { x: [ANOS[lastIdx]], y: [vals[lastIdx]], mode: 'markers', marker: { color: col, size: 5 }, hoverinfo: 'skip' },
    ], {
      ...BL,
      margin: { l: 2, r: 2, t: 4, b: 2 },
      height: 34,
      showlegend: false,
      xaxis: { visible: false },
      yaxis: { visible: false, autorange: inv ? 'reversed' : true },
    }, sparkCfg);
  };

  ED.lazySection = function (idx, fn) {
    const el = document.querySelectorAll('.secacc')[idx];
    if (!el) return;
    const go = () => { if (el.dataset.lz) return; el.dataset.lz = '1'; fn(); };
    if (el.open) requestAnimationFrame(go);
    else el.addEventListener('toggle', () => { if (el.open) requestAnimationFrame(go); });
  };

  ED.lazyDetails = function (selector, fn) {
    const el = document.querySelector(selector);
    if (!el) return;
    const go = () => { if (el.dataset.lz) return; el.dataset.lz = '1'; fn(); };
    if (el.open) requestAnimationFrame(go);
    else el.addEventListener('toggle', () => { if (el.open) requestAnimationFrame(go); });
  };
})(window.EnemDash);
