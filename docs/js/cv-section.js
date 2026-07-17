(function (ED) {
  ED.initCv = function (ctx) {
    const { DATA, ANOS, AREAKEYS, AREANOME, ACOR, BL, CFG, C } = ctx;
    const DP = DATA.desvio_padrao || {};
    const CV = DATA.cv || {};
    const hoverScore = ED.Config.hoverAreaScore || ED.Config.hoverAreaTemplate;
    const full = ED.Config.AREANOME_FULL || {};
    const dpTr = AREAKEYS.map((k) => {
      const nome = full[k] || AREANOME[k];
      return {
        x: ANOS, y: DP[k] || [], mode: 'lines', name: nome,
        line: { color: ACOR[k], width: 2 },
        hovertemplate: hoverScore(nome, 1),
      };
    });
    const mergeP = ED.Config.mergePandemia;
    const dpVals = AREAKEYS.flatMap((k) => (DP[k] || []).filter((v) => v != null));
    const dpLo = dpVals.length ? Math.min(...dpVals) - 2 : 40;
    const dpHi = dpVals.length ? Math.max(...dpVals) + 2 : 80;
    Plotly.newPlot('g_dp', dpTr, mergeP({
      ...BL, height: 300, hovermode: 'x unified',
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { title: { text: 'desvio padr\u00e3o (pts)', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)', range: [dpLo, dpHi] },
    }, { y0: dpLo, y1: dpHi }), CFG);
    const cvTr = AREAKEYS.map((k) => {
      const nome = full[k] || AREANOME[k];
      return {
        x: ANOS, y: CV[k] || [], mode: 'lines', name: nome,
        line: { color: ACOR[k], width: 2 },
        hovertemplate: ED.Config.hoverAreaTemplate(nome, '%{y:.1f}%'),
      };
    });
    const cvVals = AREAKEYS.flatMap((k) => (CV[k] || []).filter((v) => v != null));
    const cvLo = cvVals.length ? Math.min(...cvVals) - 1 : 8;
    const cvHi = cvVals.length ? Math.max(...cvVals) + 1 : 16;
    Plotly.newPlot('g_cv', cvTr, mergeP({
      ...BL, height: 300, hovermode: 'x unified',
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { title: { text: 'coef. varia\u00e7\u00e3o (%)', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)', range: [cvLo, cvHi] },
    }, { y0: cvLo, y1: cvHi }), CFG);
  };
})(window.EnemDash);
