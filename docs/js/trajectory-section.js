(function (ED) {
  function currentZeroMode() {
    return ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
  }

  function indexPointFromClick(el, ev, areaKeys) {
    if (!el || !el._fullLayout || !el.data) return null;
    const fl = el._fullLayout;
    const rect = el.getBoundingClientRect();
    const xpx = ev.clientX - rect.left - fl.margin.l;
    const ypx = ev.clientY - rect.top - fl.margin.t;
    const plotW = fl.width - fl.margin.l - fl.margin.r;
    const plotH = fl.height - fl.margin.t - fl.margin.b;
    if (xpx < 0 || ypx < 0 || xpx > plotW || ypx > plotH) return null;
    const xClick = fl.xaxis.p2d(xpx);
    const yClick = fl.yaxis.p2d(ypx);
    const xSpan = fl.xaxis.range[1] - fl.xaxis.range[0] || 1;
    const ySpan = fl.yaxis.range[1] - fl.yaxis.range[0] || 1;
    let best = null;
    let bestD = Infinity;
    el.data.forEach((tr, ci) => {
      const k = areaKeys[ci];
      if (!k) return;
      (tr.x || []).forEach((xv, i) => {
        const yv = tr.y[i];
        if (yv == null) return;
        const dx = (Number(xv) - xClick) / xSpan;
        const dy = (yv - yClick) / ySpan;
        const d = dx * dx + dy * dy;
        if (d < bestD) {
          bestD = d;
          best = { areaKey: k, ano: Number(xv) };
        }
      });
    });
    return best;
  }

  function openIndexDetail(ctx, areaKey, ano) {
    if (areaKey && ano != null) ED.showIndexDetail(ctx, areaKey, ano);
  }

  function bindIndexChartClick(ctx, gd) {
    const el = gd || document.getElementById('g_index');
    if (!el) return;
    el._indexCtx = ctx;
    if (typeof el.on === 'function') {
      if (el.removeAllListeners) el.removeAllListeners('plotly_click');
      el.on('plotly_click', (ev) => {
        const pt = ev.points && ev.points[0];
        if (!pt) return;
        const k = ctx.AREAKEYS[pt.curveNumber];
        openIndexDetail(ctx, k, Number(pt.x));
      });
    }
    if (!el._indexNativeBound) {
      el._indexNativeBound = true;
      el.addEventListener('click', (ev) => {
        const hit = indexPointFromClick(el, ev, ctx.AREAKEYS);
        if (hit) openIndexDetail(ctx, hit.areaKey, hit.ano);
      });
    }
  }

  function refreshIndexChart(ctx) {
    const el = document.getElementById('g_index');
    if (!el || !el.data) return;
    Plotly.Plots.resize(el);
    bindIndexChartClick(ctx, el);
  }

  function mountIndexChart(ctx) {
    const el = document.getElementById('g_index');
    if (!el) return;
    const { DATA, ANOS, AREAKEYS, AREANOME, ACOR, BL, CFG, C } = ctx;
    const CFGI = ED.Config.CFG_INTERACTIVE || CFG;
    const zeroMode = currentZeroMode();
    const AS = zeroMode === 'no_zero'
      ? (DATA.indexAreasSemZero || DATA.indexAreas || { CN: [], CH: [], LC: [], MT: [], RED: [] })
      : (DATA.indexAreas || { CN: [], CH: [], LC: [], MT: [], RED: [] });
    const tr = AREAKEYS.map((k) => {
      const b = AS[k][0] || 1;
      return {
        x: ANOS,
        y: AS[k].map((v) => (v != null && b ? +(v / b * 100).toFixed(1) : null)),
        mode: 'lines+markers',
        name: AREANOME[k],
        line: { color: ACOR[k], width: 2.2 },
        marker: { size: 10, symbol: 'circle', line: { width: 1, color: '#fff' } },
        hovertemplate: `${AREANOME[k]} %{x}<br>\u00edndice %{y:.1f}<extra>Clique para detalhes</extra>`,
      };
    });
    const draw = () => {
      const done = (gd) => {
        bindIndexChartClick(ctx, gd || el);
        Plotly.Plots.resize(gd || el);
      };
      const p = Plotly.react(el, tr, {
        ...BL, height: 300, dragmode: false, hovermode: 'closest',
        clickmode: 'event+select', uirevision: 'index',
        legend: { orientation: 'h', y: -0.22, font: { size: 9.5 } },
        xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
        yaxis: { title: { text: '\u00edndice (2019=100)', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
        shapes: [{ type: 'line', x0: ANOS[0], x1: ANOS[ANOS.length - 1], y0: 100, y1: 100, line: { color: C.borda, width: 1, dash: 'dot' } }],
      }, CFGI);
      if (p && typeof p.then === 'function') p.then(done);
      else done(el);
    };
    requestAnimationFrame(() => requestAnimationFrame(draw));
  }

  ED.initTrajectory = function (ctx) {
    const { DATA, ANOS, LAST_YEAR, C, BL, CFG, NF } = ctx;
    const CFGI = ED.Config.CFG_INTERACTIVE || CFG;

    document.querySelectorAll('[data-school-zero-mode]').forEach((el) => {
      if (el.dataset.zeroModeBound === '1') return;
      el.dataset.zeroModeBound = '1';
      el.onchange = () => {
        if (ED.setSchoolZeroMode) ED.setSchoolZeroMode(el.value);
      };
    });

    const gradBase = ['#9DC3E6', '#6BA6DC', '#3BA4E8', '#1A6FB5', '#0A4D8C', '#053B71', '#032C55'];
    function renderTrajectoryCharts() {
      const zeroMode = currentZeroMode();
      const TX_MS = zeroMode === 'no_zero' ? (ctx.TX_MS_SEM_ZERO || ctx.TX_MS) : ctx.TX_MS;
      const MED_MS = zeroMode === 'no_zero' ? (ctx.MED_MS_SEM_ZERO || ctx.MED_MS) : ctx.MED_MS;
      const MED_BR = zeroMode === 'no_zero' ? (ctx.MED_BR_SEM_ZERO || ctx.MED_BR) : ctx.MED_BR;
      const RANK_MS = zeroMode === 'no_zero' ? (ctx.RANK_MS_SEM_ZERO || ctx.RANK_MS) : ctx.RANK_MS;
      const estadualN = zeroMode === 'no_zero' ? (DATA.estadualNSemZero || DATA.estadualN) : DATA.estadualN;
      const ufRank = zeroMode === 'no_zero' ? (DATA.ufRankByYearSemZero || DATA.ufRankByYear) : DATA.ufRankByYear;
      const grad = ANOS.map((_, idx) => gradBase[Math.min(idx, gradBase.length - 1)]);
      const txVals = TX_MS.filter((v) => v != null);
      const medVals = MED_MS.filter((v) => v != null);
      Plotly.react('g_traj', [{
        x: TX_MS, y: MED_MS, mode: 'lines+markers+text',
        line: { color: 'rgba(10,77,140,.45)', width: 2 },
        marker: { size: ANOS.map((a) => (a === LAST_YEAR ? 16 : 11)), color: grad, line: { color: '#fff', width: 1.5 } },
        text: ANOS.map(String), textposition: 'bottom center', textfont: { size: 10, color: C.muted },
        customdata: estadualN.map((n) => NF(n)),
        hovertemplate: '<b>%{text}</b><br>Part.: %{x:.1f}% \u00b7 %{customdata} participantes efetivos<br>M\u00e9dia: %{y:.1f}<extra></extra>',
      }], {
        ...BL, height: 300, showlegend: false,
        xaxis: {
          title: { text: 'participa\u00e7\u00e3o efetiva (% dos concluintes)', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          range: [Math.max(0, Math.min(...txVals) - 3), Math.max(...txVals) + 5],
        },
        yaxis: {
          title: { text: 'm\u00e9dia geral', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          range: [Math.min(...medVals) - 4, Math.max(...medVals) + 4],
        },
        annotations: [{
          x: TX_MS[ANOS.length - 1], y: MED_MS[ANOS.length - 1], ax: TX_MS[ANOS.length - 2], ay: MED_MS[ANOS.length - 2],
          xref: 'x', yref: 'y', axref: 'x', ayref: 'y',
          showarrow: true, arrowhead: 3, arrowsize: 1.4, arrowwidth: 2, arrowcolor: C.azulEsc,
        }],
      }, CFGI);

      ED.initIndexDrillUi(ctx);
      mountIndexChart(ctx);

      const yMin = Math.min(...RANK_MS.filter((v) => v != null)) - 2;
      const yMax = Math.max(...RANK_MS.filter((v) => v != null)) + 2;
      const medLo = Math.min(...MED_MS.concat(MED_BR).filter((v) => v != null)) - 3;
      const medHi = Math.max(...MED_MS.concat(MED_BR).filter(v => v != null)) + 3;

      Plotly.react('g_bump', [{
        x: ANOS, y: RANK_MS, mode: 'lines+markers+text',
        line: { color: C.laranja, width: 3 },
        marker: { size: 15, color: C.laranja, line: { color: '#fff', width: 1.5 } },
        text: RANK_MS.map((r) => (r != null ? `${r}\u00ba` : '')),
        textposition: 'middle center', textfont: { size: 8.5, color: '#fff' },
        hovertemplate: '%{x}: %{y}\u00ba de 27<extra></extra>',
      }], {
        ...BL, height: 280, showlegend: false,
        xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
        yaxis: {
          autorange: 'reversed', dtick: 2, gridcolor: 'rgba(0,0,0,0)',
          title: { text: 'posi\u00e7\u00e3o (1=melhor)', font: { size: 10 } },
          range: [yMax, yMin],
        },
      }, CFGI);

      Plotly.react('g_evol', [
        { x: ANOS, y: MED_BR, mode: 'lines+markers', name: 'Brasil estadual', line: { color: C.brasil, width: 2, dash: 'dot' }, marker: { size: 6 } },
        {
          x: ANOS, y: MED_MS, mode: 'lines+markers+text', name: 'MS estadual',
          line: { color: C.azul, width: 2.6 }, marker: { size: 7 },
          text: MED_MS.map((v) => (v != null ? v.toFixed(0) : '')),
          textposition: 'bottom center', textfont: { size: 9, color: C.azulEsc },
        },
      ], {
        ...BL, height: 280,
        legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
        xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
        yaxis: { range: [medLo, medHi], gridcolor: 'rgba(0,0,0,0)' },
        shapes: [{ type: 'rect', x0: 2019.6, x1: 2021.4, y0: medLo, y1: medHi, fillcolor: 'rgba(120,135,148,.10)', line: { width: 0 } }],
        annotations: [{ x: 2020.5, y: medHi - 1, text: 'pandemia', showarrow: false, font: { size: 9, color: C.muted } }],
      }, CFGI);

      const bumpEl = document.getElementById('notaBump');
      if (bumpEl && ufRank[String(LAST_YEAR)]?.length) {
        bumpEl.textContent = zeroMode === 'no_zero'
          ? 'Filtro ativo: excluindo participantes com alguma nota zero no cálculo das posições e médias.'
          : 'Filtro ativo: incluindo todos os participantes efetivos, inclusive com nota zero.';
      }
      const evolEl = document.getElementById('notaEvol');
      if (evolEl) {
        evolEl.textContent = zeroMode === 'no_zero'
          ? 'MS e Brasil estadual recalculados sem participantes com qualquer nota zero.'
          : 'MS e Brasil estadual calculados com todos os participantes efetivos.';
      }
    }

    renderTrajectoryCharts();

    const trajSec = document.querySelector('.secacc');
    const indexEl = document.getElementById('g_index');
    if (trajSec) {
      trajSec.addEventListener('toggle', () => {
        if (trajSec.open) requestAnimationFrame(() => refreshIndexChart(ctx));
      });
    }
    window.addEventListener('load', () => requestAnimationFrame(() => refreshIndexChart(ctx)));
    if (indexEl && typeof IntersectionObserver !== 'undefined') {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) requestAnimationFrame(() => refreshIndexChart(ctx));
        });
      }, { threshold: 0.15 });
      io.observe(indexEl);
    }
    document.addEventListener('enemdash:schoolZeroMode', renderTrajectoryCharts);
  };
})(window.EnemDash);
