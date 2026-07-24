(function (ED) {
  ED.initInteg = function (ctx) {
    const { DATA, LAST_INDEX, LAST_YEAR, C, BL, CFG, NF } = ctx;
    const INT = DATA.integ || {};
    const AN = DATA.anos || [];
    const ICOL = { CN: '#9B59B6', CH: '#3498DB', LC: '#1ABC9C', MT: '#F1C40F', RED: '#E74C3C' };

    let attMode = 'cre';
    let attFilterCre = null;
    let attYearIdx = LAST_INDEX;

    function renderElim(dep) {
      const d = INT.rede[dep];
      if (!d) return;
      const txMax = Math.max(...(d.txE || []).filter((v) => v != null), 0) + 1;
      const elimMax = Math.max(
        ...AN.map((_, i) => (
          (d.areaElim?.CN?.[i] || 0)
          + (d.areaElim?.CH?.[i] || 0)
          + (d.areaElim?.LC?.[i] || 0)
          + (d.areaElim?.MT?.[i] || 0)
          + (d.er?.[i] || 0)
        )),
        0,
      ) + 5;
      const bars = [
        { x: AN, y: d.areaElim.CN, name: 'CN', type: 'bar', marker: { color: ICOL.CN }, hovertemplate: 'CN elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.areaElim.CH, name: 'CH', type: 'bar', marker: { color: ICOL.CH }, hovertemplate: 'CH elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.areaElim.LC, name: 'LC', type: 'bar', marker: { color: ICOL.LC }, hovertemplate: 'LC elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.areaElim.MT, name: 'MT', type: 'bar', marker: { color: ICOL.MT }, hovertemplate: 'MT elim. %{x}: %{y}<extra></extra>' },
        { x: AN, y: d.er, name: 'Redacao (anulada)', type: 'bar', marker: { color: ICOL.RED }, hovertemplate: 'Redacao anulada %{x}: %{y}<extra></extra>' },
      ];
      const line = {
        x: AN, y: d.txE, mode: 'lines', name: 'Taxa elim. (%)', yaxis: 'y2',
        line: { color: C.critico, width: 2 },
        hovertemplate: 'Taxa eliminacao %{x}: %{y:.2f}%<extra></extra>',
      };
      Plotly.newPlot('g_integ_elim', bars.concat([line]), ED.withPandemia({
        ...BL, height: 300, barmode: 'stack',
        xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
        yaxis: { title: { text: 'eliminados', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)', range: [0, elimMax] },
        yaxis2: {
          overlaying: 'y', side: 'right',
          title: { text: '% do compareceu', font: { size: 10 } },
          showgrid: false, tickfont: { size: 10 },
          range: [0, Math.max(txMax, 5)],
        },
        legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
      }, { y0: 0, y1: elimMax, annotate: false }), CFG);
    }

    const sel = document.getElementById('integRedeSel');
    if (sel) {
      sel.innerHTML = '';
      ['Estadual', 'Federal', 'Municipal', 'Privada', 'Brasil-Estadual'].forEach((o) => {
        const op = document.createElement('option');
        op.value = o;
        op.textContent = o === 'Brasil-Estadual' ? 'Brasil \u00b7 rede estadual' : o;
        sel.appendChild(op);
      });
      sel.value = 'Estadual';
      sel.onchange = () => renderElim(sel.value);
    }
    renderElim('Estadual');

    const comps = INT.rede || {};
    const depOrd = ['Estadual', 'Federal', 'Municipal', 'Privada', 'Brasil-Estadual'];
    const compX = depOrd.filter((k) => comps[k]);
    const txE2024 = compX.map((k) => comps[k].txE[LAST_INDEX]);
    const txS2024 = compX.map((k) => comps[k].txS[LAST_INDEX]);
    Plotly.newPlot('g_integ_comp', [
      { x: compX, y: txE2024, name: 'Taxa eliminacao (%)', type: 'bar', marker: { color: C.critico }, hovertemplate: '%{x}<br>Eliminacao: %{y:.2f}%<extra></extra>' },
      { x: compX, y: txS2024, name: 'Redacao em branco (%)', type: 'bar', marker: { color: C.azul }, hovertemplate: '%{x}<br>Em branco (TP_STATUS=4): %{y:.2f}%<extra></extra>' },
    ], {
      ...BL, height: 300, barmode: 'group',
      xaxis: { tickfont: { size: 11 } },
      yaxis: { title: { text: '%', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
      legend: { orientation: 'h', y: -0.22, font: { size: 9 } },
    }, CFG);

    const anoSel = document.getElementById('integAttAno');
    const yearLabel = document.getElementById('integAttYearLabel');
    const yearCoh = document.getElementById('integAttYearCoh');

    function selectedYear() {
      return AN[attYearIdx] ?? LAST_YEAR;
    }

    function syncYearLabels() {
      const y = String(selectedYear());
      if (yearLabel) yearLabel.textContent = y;
      if (yearCoh) yearCoh.textContent = y;
    }

    function seriesAt(o, key, idx) {
      const arr = o?.[key];
      if (!arr || idx < 0 || idx >= arr.length) return null;
      const v = arr[idx];
      return v == null || Number.isNaN(v) ? null : v;
    }

    function renderIntegTable(mode, filterCre) {
      if (mode) attMode = mode;
      if (arguments.length > 1) attFilterCre = filterCre || null;
      const host = document.getElementById('g_integ_table');
      if (!host) return;
      const idx = attYearIdx;
      const year = selectedYear();
      syncYearLabels();

      let rows = [];
      if (attMode === 'cre') {
        Object.entries(INT.cre || {}).forEach(([name, o]) => {
          const filt = seriesAt(o, 'filt', idx);
          if (filt == null && seriesAt(o, 'txE', idx) == null) return;
          rows.push({
            nome: ED.creDisplay(name),
            cre: name,
            filt: filt || 0,
            et: seriesAt(o, 'et', idx) || 0,
            em: seriesAt(o, 'em', idx) || 0,
            zm: seriesAt(o, 'zm', idx) || 0,
            sm: seriesAt(o, 'sm', idx) || 0,
            txE: seriesAt(o, 'txE', idx),
            txS: seriesAt(o, 'txS', idx),
            tipo: 'cre',
            key: name,
          });
        });
      } else {
        Object.entries(INT.mun || {}).forEach(([name, o]) => {
          if (attFilterCre && o.cre !== attFilterCre) return;
          const filt = seriesAt(o, 'filt', idx);
          if (filt == null && seriesAt(o, 'txE', idx) == null) return;
          rows.push({
            nome: name,
            cre: ED.creDisplay(o.cre),
            filt: filt || 0,
            et: seriesAt(o, 'et', idx) || 0,
            em: seriesAt(o, 'em', idx) || 0,
            zm: seriesAt(o, 'zm', idx) || 0,
            sm: seriesAt(o, 'sm', idx) || 0,
            txE: seriesAt(o, 'txE', idx),
            txS: seriesAt(o, 'txS', idx),
            tipo: 'mun',
            key: name,
          });
        });
      }
      rows.sort((a, b) => (b.txE || 0) - (a.txE || 0));
      const est = INT.rede.Estadual || {};
      const medE = seriesAt(est, 'txE', idx);
      const medS = seriesAt(est, 'txS', idx);
      let html = `<div class="scroll"><table class="attbl"><thead><tr><th>${attMode === 'cre' ? 'CRE' : 'Municipio'
      }</th><th>Part. efetivos</th><th>Eliminados</th><th>Taxa elim. (%)</th><th>Sem nota red.</th><th>Taxa sem nota (%)</th><th title="Eliminados em >=2 areas objetivas">Elim. multipla</th><th title="Zeros em >=2 areas">Zeros multiplo</th><th title="Sem nota em >=2 areas objetivas">Sem nota multipla</th></tr></thead><tbody>`;
      if (!rows.length) {
        html += `<tr><td colspan="9" style="text-align:center;color:${C.muted};padding:18px">Sem dados de integridade territorial para ${year}.</td></tr>`;
      }
      rows.forEach((r) => {
        const warnE = medE != null && (r.txE || 0) > medE;
        const warnS = medS != null && (r.txS || 0) > medS;
        const esc = String(r.key || r.nome).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        html += `<tr onclick="integClick('${r.tipo}','${esc}')">`
          + `<td><b>${r.nome}</b>${attMode === 'cre' ? '' : ` <span style="font-size:11px;color:${C.borda}">${r.cre}</span>`}</td>`
          + `<td>${NF(r.filt)}</td><td>${r.et}</td>`
          + `<td style="color:${warnE ? C.critico : ''}">${r.txE != null ? r.txE.toFixed(2) : '\u2014'}</td>`
          + `<td>${r.filt > 0 && r.txS != null ? Math.round(r.filt * r.txS / 100) : '\u2014'}</td>`
          + `<td style="color:${warnS ? '#E67E22' : ''}">${r.txS != null ? r.txS.toFixed(2) : '\u2014'}</td>`
          + `<td>${r.em || '\u2014'}</td><td>${r.zm || '\u2014'}</td><td>${r.sm || '\u2014'}</td></tr>`;
      });
      html += '</tbody></table></div>';
      if (attMode === 'mun') {
        const creLbl = attFilterCre ? ED.creDisplay(attFilterCre) : '';
        html = `<div style="margin-bottom:8px"><span class="pill" style="cursor:pointer" onclick="renderIntegTable('cre')">\u2190 Voltar as CREs</span>`
          + (creLbl ? ` <span style="font-size:12px;color:${C.muted}">· ${creLbl} · ${year}</span>` : '')
          + '</div>' + html;
      }
      host.innerHTML = html;
    }

    if (anoSel) {
      AN.forEach((a) => {
        const o = document.createElement('option');
        o.value = String(a);
        o.textContent = a;
        anoSel.appendChild(o);
      });
      anoSel.value = String(LAST_YEAR);
      anoSel.onchange = () => {
        const y = Number(anoSel.value);
        const i = AN.indexOf(y);
        attYearIdx = i >= 0 ? i : LAST_INDEX;
        renderIntegTable(attMode, attFilterCre);
      };
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
