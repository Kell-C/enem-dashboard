(function (ED) {
  ED.initInteg = function (ctx) {
    const { DATA, C, BL, CFG, NF } = ctx;
    const INT = DATA.integ || {};
    const AN = DATA.anos;
    const ICOL = { CN: '#9B59B6', CH: '#3498DB', LC: '#1ABC9C', MT: '#F1C40F', RED: '#E74C3C' };

    function renderElim(dep) {
      const d = INT.rede[dep];
      if (!d) return;
      const bars = [
        { x: AN, y: d.areaElim.CN, name: 'CN', type: 'bar', marker: { color: ICOL.CN }, hovertemplate: 'CN elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.areaElim.CH, name: 'CH', type: 'bar', marker: { color: ICOL.CH }, hovertemplate: 'CH elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.areaElim.LC, name: 'LC', type: 'bar', marker: { color: ICOL.LC }, hovertemplate: 'LC elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.areaElim.MT, name: 'MT', type: 'bar', marker: { color: ICOL.MT }, hovertemplate: 'MT elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.er, name: 'Redacao', type: 'bar', marker: { color: ICOL.RED }, hovertemplate: 'Redacao elim. %{x}: %{y}<extra></extra>' },
      ];
      const line = {
        x: AN, y: d.txE, mode: 'lines+markers', name: 'Taxa elim. (%)', yaxis: 'y2',
        line: { color: C.critico, width: 2 }, marker: { size: 5 },
        hovertemplate: 'Taxa eliminacao %{x}: %{y:.2f}%<extra></extra>',
      };
      Plotly.newPlot('g_integ_elim', bars.concat([line]), {
        ...BL, height: 300, barmode: 'stack',
        xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
        yaxis: { title: { text: 'eliminados', font: { size: 10 } }, gridcolor: C.subtle },
        yaxis2: {
          overlaying: 'y', side: 'right',
          title: { text: '% do compareceu', font: { size: 10 } },
          showgrid: false, tickfont: { size: 10 },
        },
        legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      }, CFG);
    }

    const sel = document.createElement('select');
    sel.style.cssText = `margin-top:8px;padding:4px 8px;border:1px solid ${C.borda};border-radius:6px;font-size:12px;background:#fff;color:${C.azul}`;
    ['Estadual', 'Federal', 'Municipal', 'Privada', 'Brasil-Estadual'].forEach((o) => {
      const op = document.createElement('option');
      op.value = o;
      op.textContent = o === 'Brasil-Estadual' ? 'Brasil \u00b7 rede estadual' : o;
      sel.appendChild(op);
    });
    sel.value = 'Estadual';
    sel.onchange = () => renderElim(sel.value);
    document.getElementById('g_integ_elim').parentNode.appendChild(sel);
    renderElim('Estadual');

    const comps = INT.rede || {};
    const depOrd = ['Estadual', 'Federal', 'Municipal', 'Privada', 'Brasil-Estadual'];
    const compX = depOrd.filter((k) => comps[k]);
    const txE2024 = compX.map((k) => comps[k].txE[5]);
    const txS2024 = compX.map((k) => comps[k].txS[5]);
    Plotly.newPlot('g_integ_comp', [
      { x: compX, y: txE2024, name: 'Taxa eliminacao (%)', type: 'bar', marker: { color: C.critico }, hovertemplate: '%{x}<br>Eliminacao: %{y:.2f}%<extra></extra>' },
      { x: compX, y: txS2024, name: 'Sem nota redacao (%)', type: 'bar', marker: { color: C.azul }, hovertemplate: '%{x}<br>Sem nota: %{y:.2f}%<extra></extra>' },
    ], {
      ...BL, height: 300, barmode: 'group',
      xaxis: { tickfont: { size: 11 } },
      yaxis: { title: { text: '%', font: { size: 10 } }, gridcolor: C.subtle },
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
    }, CFG);

    function renderIntegTable(mode, filterCre) {
      const host = document.getElementById('g_integ_table');
      let rows = [];
      if (mode === 'cre') {
        Object.entries(INT.cre || {}).forEach(([name, o]) => {
          const i5 = 5;
          rows.push({
            nome: name, cre: name, filt: o.filt[i5] || 0, et: o.et[i5] || 0,
            em: o.em[i5] || 0, zm: o.zm[i5] || 0, sm: o.sm[i5] || 0,
            txE: o.txE[i5], txS: o.txS[i5], tipo: 'cre',
          });
        });
      } else {
        Object.entries(INT.mun || {}).forEach(([name, o]) => {
          if (filterCre && o.cre !== filterCre) return;
          const i5 = 5;
          rows.push({
            nome: name, cre: o.cre, filt: o.filt[i5] || 0, et: o.et[i5] || 0,
            em: o.em[i5] || 0, zm: o.zm[i5] || 0, sm: o.sm[i5] || 0,
            txE: o.txE[i5], txS: o.txS[i5], tipo: 'mun',
          });
        });
      }
      rows.sort((a, b) => (b.txE || 0) - (a.txE || 0));
      const est = INT.rede.Estadual || {};
      const medE = est.txE ? est.txE[5] : null;
      const medS = est.txS ? est.txS[5] : null;
      let html = `<div class="scroll"><table class="attbl"><thead><tr><th>${mode === 'cre' ? 'CRE' : 'Municipio'
      }</th><th>Part. efetivos</th><th>Eliminados</th><th>Taxa elim. (%)</th><th>Sem nota red.</th><th>Taxa sem nota (%)</th><th title="Eliminados em >=2 areas objetivas">Elim. multipla</th><th title="Zeros em >=2 areas">Zeros multiplo</th><th title="Sem nota em >=2 areas objetivas">Sem nota multipla</th></tr></thead><tbody>`;
      rows.forEach((r) => {
        const warnE = medE != null && (r.txE || 0) > medE;
        const warnS = medS != null && (r.txS || 0) > medS;
        const esc = String(r.nome).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        html += `<tr onclick="integClick('${r.tipo}','${esc}')">`
          + `<td><b>${r.nome}</b>${mode === 'cre' ? '' : ` <span style="font-size:11px;color:${C.borda}">${r.cre}</span>`}</td>`
          + `<td>${NF(r.filt)}</td><td>${r.et}</td>`
          + `<td style="color:${warnE ? C.critico : ''}">${r.txE != null ? r.txE.toFixed(2) : '\u2014'}</td>`
          + `<td>${r.et > 0 ? Math.round(r.filt * r.txS / 100) : '\u2014'}</td>`
          + `<td style="color:${warnS ? '#E67E22' : ''}">${r.txS != null ? r.txS.toFixed(2) : '\u2014'}</td>`
          + `<td>${r.em || '\u2014'}</td><td>${r.zm || '\u2014'}</td><td>${r.sm || '\u2014'}</td></tr>`;
      });
      html += '</tbody></table></div>';
      if (mode === 'mun') {
        html = '<div style="margin-bottom:8px"><span class="pill" style="cursor:pointer" onclick="renderIntegTable(\'cre\')">\u2190 Voltar as CREs</span></div>' + html;
      }
      host.innerHTML = html;
    }

    window.renderIntegTable = renderIntegTable;
    window.integClick = function (tipo, nome) {
      if (tipo === 'cre') renderIntegTable('mun', nome);
      else if (tipo === 'mun') {
        window.selectMun(nome);
        document.getElementById('escCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    };
    renderIntegTable('cre');
  };
})(window.EnemDash);
