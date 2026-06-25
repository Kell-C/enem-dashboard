(function (ED) {
  ED.initRedes = function (ctx) {
    const { DATA, ANOS, LAST_YEAR, AREAKEYS, C, BL, CFG, NF } = ctx;
    const RC = { Estadual: C.azul, Municipal: C.dourado, Federal: C.verde, Privada: C.roxo };
    const RN = {
      Estadual: 'Estadual (MS)', Municipal: 'Municipal (MS)',
      Federal: 'Federal (MS)', Privada: 'Privada (MS)',
    };
    const deps = Object.keys(DATA.redes || {});
    const tr = deps.map((dep) => {
      const est = dep === 'Estadual';
      const mun = dep === 'Municipal';
      const t = {
        x: ANOS, y: DATA.redes[dep].med,
        mode: `lines${est ? '+markers' : ''}`,
        name: `${RN[dep]}${mun ? ' \u00b7 N pequeno' : ''}`,
        line: { color: RC[dep], width: est ? 3.4 : 1.8, dash: mun ? 'dot' : 'solid' },
        hovertemplate: `${RN[dep]} %{x}<br>M\u00e9dia: %{y:.0f}<br>Participantes efetivos: %{customdata}<extra></extra>`,
        customdata: DATA.redes[dep].n.map((n) => NF(n)),
      };
      if (est) t.marker = { size: 6 };
      return t;
    });
    Plotly.newPlot('g_redes', tr, {
      ...BL, height: 300,
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { title: { text: 'm\u00e9dia geral', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
    }, CFG);

    const others = deps.filter((d) => d !== 'Estadual');
    const estA = DATA.redes.Estadual.areas;
    const gapAno = document.getElementById('redeGapAno');
    ANOS.forEach((a) => {
      const o = document.createElement('option');
      o.value = a;
      o.textContent = a;
      gapAno.appendChild(o);
    });
    gapAno.value = String(LAST_YEAR);

    function renderRedeGap(ano) {
      const i = ANOS.indexOf(Number(ano));
      if (i < 0) return;
      const gtr = others.map((dep) => ({
        x: AREAKEYS,
        y: AREAKEYS.map((k) => +(estA[k][i] - DATA.redes[dep].areas[k][i]).toFixed(0)),
        type: 'bar', name: RN[dep], marker: { color: RC[dep] },
        hovertemplate: `${RN[dep]} \u00b7 %{x}: %{y}<extra></extra>`,
      }));
      Plotly.react('g_redegap', gtr, {
        ...BL, height: 300, barmode: 'group',
        legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
        xaxis: { tickfont: { size: 11 } },
        yaxis: {
          title: { text: 'estadual \u2212 rede (pontos)', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)', zeroline: true, zerolinecolor: C.borda, zerolinewidth: 1.4,
        },
      }, CFG);
      const titleEl = document.getElementById('redeGapTitle');
      if (titleEl && titleEl.childNodes[0]) {
        titleEl.childNodes[0].nodeValue = `Dist\u00e2ncia por \u00e1rea \u00b7 estadual \u2212 outras redes de MS (${ano}) `;
      }
    }
    gapAno.onchange = (e) => renderRedeGap(parseInt(e.target.value, 10));
    renderRedeGap(LAST_YEAR);
  };
})(window.EnemDash);
