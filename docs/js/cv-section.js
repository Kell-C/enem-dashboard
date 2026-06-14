(function (ED) {
  ED.initCv = function (ctx) {
    const { DATA, ANOS, AREAKEYS, AREANOME, ACOR, BL, CFG, C } = ctx;
    const DP = DATA.desvio_padrao || {};
    const CV = DATA.cv || {};
    const dpTr = AREAKEYS.map((k) => ({
      x: ANOS, y: DP[k] || [], mode: 'lines+markers', name: AREANOME[k],
      line: { color: ACOR[k], width: 2 }, marker: { size: 5 },
      hovertemplate: `${AREANOME[k]} %{x}<br>DP: %{y:.1f} pts<extra></extra>`,
    }));
    Plotly.newPlot('g_dp', dpTr, {
      ...BL, height: 300,
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { title: { text: 'desvio padr\u00e3o (pts)', font: { size: 10 } }, gridcolor: C.subtle },
    }, CFG);
    const cvTr = AREAKEYS.map((k) => ({
      x: ANOS, y: CV[k] || [], mode: 'lines+markers', name: AREANOME[k],
      line: { color: ACOR[k], width: 2 }, marker: { size: 5 },
      hovertemplate: `${AREANOME[k]} %{x}<br>CV: %{y:.1f}%<extra></extra>`,
    }));
    Plotly.newPlot('g_cv', cvTr, {
      ...BL, height: 300,
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { title: { text: 'coef. varia\u00e7\u00e3o (%)', font: { size: 10 } }, gridcolor: C.subtle },
    }, CFG);
  };
})(window.EnemDash);
