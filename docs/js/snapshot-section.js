(function (ED) {
  ED.initSnapshot = function (ctx) {
    const { DATA, ANOS, LAST_YEAR, C, BL, CFG } = ctx;
    const AREAS = ['CN', 'CH', 'LC', 'Mat.', 'Reda\u00e7\u00e3o'];
    const AKEYS = ['CN', 'CH', 'LC', 'MT', 'RED'];
    const UF_RANK = DATA.ufRankByYear || {};
    const UF_RANK_SEM_ZERO = DATA.ufRankByYearSemZero || {};
    document.querySelectorAll('[data-school-zero-mode]').forEach((el) => {
      if (el.dataset.zeroModeBound === '1') return;
      el.dataset.zeroModeBound = '1';
      el.onchange = () => {
        if (ED.setSchoolZeroMode) ED.setSchoolZeroMode(el.value);
      };
    });

    function renderSnap(ano) {
      const i = ANOS.indexOf(ano);
      const zeroMode = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
      const porArea = ED.getPopulationMode ? ED.getPopulationMode() === 'por_area' : false;
      const areaData = porArea
        ? (zeroMode === 'no_zero'
          ? (DATA.msAreaPorAreaSemZero || DATA.msAreaSemZero || DATA.msArea || {})
          : (DATA.msAreaPorArea || DATA.msArea || {}))
        : (zeroMode === 'no_zero' ? (DATA.msAreaSemZero || DATA.msArea || {}) : (DATA.msArea || {}));
      const ufRankData = zeroMode === 'no_zero' ? UF_RANK_SEM_ZERO : UF_RANK;
      const ms = AKEYS.map((k) => (areaData[k] && areaData[k].ms ? areaData[k].ms[i] : null));
      const br = AKEYS.map((k) => (areaData[k] && areaData[k].br ? areaData[k].br[i] : null));
      const t = [];
      for (let j = 0; j < AREAS.length; j++) {
        const up = ms[j] >= br[j];
        t.push({
          x: [br[j], ms[j]], y: [AREAS[j], AREAS[j]], mode: 'lines',
          line: { color: up ? C.verde : C.critico, width: 3 },
          hoverinfo: 'skip', showlegend: false,
        });
      }
      t.push({ x: br, y: AREAS, mode: 'markers', marker: { color: C.brasil, size: 12 }, hovertemplate: 'Brasil %{x:.0f}<extra></extra>' });
      t.push({
        x: ms, y: AREAS, mode: 'markers+text', marker: { color: C.azul, size: 13 },
        text: ms.map((v, j) => { const d = v - br[j]; return `${d >= 0 ? '+' : ''}${d.toFixed(0)}`; }),
        textposition: ms.map((v, j) => (v >= br[j] ? 'middle right' : 'middle left')),
        textfont: { size: 10, color: C.azulEsc },
        hovertemplate: 'MS %{x:.0f}<extra></extra>',
      });
      Plotly.react('g_areas', t, {
        ...BL, height: 260, showlegend: false,
        xaxis: { range: [455, 655], gridcolor: 'rgba(0,0,0,0)' },
        yaxis: { autorange: 'reversed' },
      }, CFG);

      const d = ufRankData[String(ano)] || [];
      const med = d.reduce((s, r) => s + r[1], 0) / d.length;
      Plotly.react('g_ufrank', [{
        x: d.map((r) => r[0]), y: d.map((r) => r[1]), type: 'bar',
        marker: { color: d.map((r) => (r[0] === 'MS' ? C.laranja : C.azul)) },
        hovertemplate: '%{x}: %{y}<extra></extra>',
      }], {
        ...BL, height: 260,
        yaxis: { range: [480, 555], gridcolor: 'rgba(0,0,0,0)' },
        xaxis: { tickfont: { size: 9 } },
        shapes: [{ type: 'line', x0: -0.5, x1: 26.5, y0: med, y1: med, line: { color: C.critico, width: 1.5, dash: 'dash' } }],
      }, CFG);

      document.getElementById('snapDumbTitle').childNodes[0].nodeValue = `MS \u00d7 Brasil por \u00e1rea \u00b7 ${ano} (dumbbell) `;
      document.getElementById('snapRankTitle').childNodes[0].nodeValue = `Ranking das UFs \u00b7 ${ano} `;
    }

    document.getElementById('snapAno').onchange = (e) => renderSnap(parseInt(e.target.value, 10));
    document.addEventListener('enemdash:schoolZeroMode', () => {
      renderSnap(parseInt(document.getElementById('snapAno').value, 10));
    });
    document.addEventListener('enemdash:populationMode', () => {
      renderSnap(parseInt(document.getElementById('snapAno').value, 10));
    });
    renderSnap(LAST_YEAR);
  };
})(window.EnemDash);
