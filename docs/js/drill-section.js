(function (ED) {
  let SEL_CRE = null;
  let SEL_MUN = null;
  let SEL_ESC = null;
  let _ctx = null;

  function bread() {
    const b = document.getElementById('bread');
    let h = `<span class="crumb ${SEL_CRE ? '' : 'active'}" onclick="resetDrill()">Estado \u00b7 MS</span>`;
    if (SEL_CRE) {
      h += `<span class="sepc">\u2192</span><span class="crumb ${SEL_MUN ? '' : 'active'}" onclick="selectCre('${SEL_CRE.replace(/'/g, "\\'")}')">${SEL_CRE}</span>`;
    }
    if (SEL_MUN) {
      h += `<span class="sepc">\u2192</span><span class="crumb active">${SEL_MUN}</span>`;
    }
    b.innerHTML = h;
  }

  function _getAreaRefData() {
    const porArea = ED.getPopulationMode ? ED.getPopulationMode() === 'por_area' : false;
    return porArea
      ? (_ctx.DATA.msAreaPorArea || _ctx.DATA.msArea || {})
      : (_ctx.DATA.msArea || {});
  }

  function renderAreas(containerId, areas, refMap) {
    const ctx = _ctx;
    const { ANOS, DATA, AREANOME, ACOR, C, BL, CFG } = ctx;
    const msAreaRef = _getAreaRefData();
    const host = document.getElementById(containerId);
    host.innerHTML = '';
    ctx.AREAKEYS.forEach((k) => {
      const v = areas[k];
      const last = v[v.length - 1];
      const ref = refMap[k];
      const warn = last < ref;
      const tile = document.createElement('div');
      tile.className = `atile${warn ? ' warn' : ''}`;
      const delta = last - ref;
      tile.innerHTML = `<div class="at"><span>${k}</span><span class="fl" style="color:${warn ? C.critico : C.verde}">${delta >= 0 ? '+' : ''}${delta.toFixed(0)}</span></div><div id="${containerId}_${k}" style="height:74px"></div>`;
      host.appendChild(tile);
      const msRef = msAreaRef[k]?.ms || DATA.msArea?.[k]?.ms || [];
      Plotly.newPlot(`${containerId}_${k}`, [
        { x: ANOS, y: msRef, mode: 'lines', line: { color: C.brasil, width: 1.4, dash: 'dot' }, hovertemplate: `${AREANOME[k]} \u00b7 MS estadual<br><b>%{x}</b> \u00b7 %{y:.0f} pts<extra></extra>` },
        { x: ANOS, y: v, mode: 'lines+markers', line: { color: ACOR[k], width: 2 }, marker: { size: 3 }, hovertemplate: `${AREANOME[k]}<br><b>%{x}</b> \u00b7 %{y:.0f} pts<extra></extra>` },
      ], {
        ...BL, height: 74, margin: { l: 4, r: 6, t: 4, b: 14 },
        showlegend: false, xaxis: { visible: false }, yaxis: { visible: false },
      }, CFG);
    });
  }

  function setSelectedSchoolRow(schoolId) {
    document.querySelectorAll('#escBody tr').forEach((tr) => {
      tr.classList.toggle('is-sel', tr.dataset.schoolId === schoolId);
    });
  }

  function renderSchoolHistory(munName, schoolId) {
    const ctx = _ctx;
    const { DATA, ANOS, LAST_YEAR, AREANOME, ACOR, BL, CFG, NF } = ctx;
    const host = document.getElementById('g_esc_hist');
    const title = document.getElementById('escHistTitle');
    const note = document.getElementById('escHistNota');
    if (!host || !title || !note) return;

    const school = DATA.escHist?.[munName]?.[schoolId];
    if (!school) {
      title.textContent = 'Histórico da escola selecionada';
      note.textContent = '';
      host.innerHTML = '<p class="idx-empty">Histórico indisponível para a escola selecionada.</p>';
      return;
    }

    const zeroMode = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    const series = zeroMode === 'no_zero' ? (school.semZero || {}) : school;
    const histYears = ANOS.filter((ano) => ano >= 2024);
    const histIdx = histYears.map((ano) => ANOS.indexOf(ano)).filter((idx) => idx >= 0);
    const geral = histIdx.map((idx) => (series.geral || school.geral || [])[idx] ?? null);
    const vals = [];
    const areasByYear = {};
    ctx.AREAKEYS.forEach((k) => {
      areasByYear[k] = histIdx.map((idx) => (series.areas?.[k] || [])[idx] ?? null);
      areasByYear[k].forEach((v) => { if (v != null) vals.push(v); });
    });
    geral.forEach((v) => { if (v != null) vals.push(v); });
    if (!vals.length) {
      title.textContent = `${school.nome} · histórico`;
      note.textContent = 'Sem série histórica suficiente com o filtro atual.';
      host.innerHTML = '<p class="idx-empty">Sem dados históricos para exibir com os parâmetros atuais.</p>';
      return;
    }

    const custom = histYears.map((ano, pos) => {
      const idx = histIdx[pos];
      return [
      ano,
      NF(series.part?.[idx] || 0),
      NF(school.concl?.[idx] || 0),
      series.tx?.[idx] != null ? `${series.tx[idx].toFixed(1)}%` : '—',
      geral[pos] != null ? geral[pos].toFixed(1) : '—',
      school.mun || munName,
      school.cre || '—',
      ];
    });
    const traces = ctx.AREAKEYS.map((k) => ({
      x: histYears,
      y: areasByYear[k],
      customdata: custom,
      mode: 'lines+markers',
      name: AREANOME[k],
      line: { color: ACOR[k], width: 2 },
      marker: { size: 6 },
      hovertemplate: `<b>${school.nome}</b><br>%{customdata[0]} · ${AREANOME[k]}: %{y:.1f}<br>`
        + 'Município: %{customdata[5]}<br>'
        + 'CRE: %{customdata[6]}<br>'
        + 'Part. efetivos: %{customdata[1]}<br>'
        + 'Concluintes: %{customdata[2]}<br>'
        + 'Tx: %{customdata[3]}<br>'
        + 'Média geral: %{customdata[4]}<extra></extra>',
    }));
    traces.push({
      x: histYears,
      y: geral,
      customdata: custom,
      mode: 'lines+markers',
      name: 'Média geral',
      line: { color: '#E67E22', width: 3 },
      marker: { size: 7, symbol: 'diamond', line: { color: '#fff', width: 1 } },
      hovertemplate: `<b>${school.nome}</b><br>%{customdata[0]} · Média geral: %{y:.1f}<br>`
        + 'Município: %{customdata[5]}<br>'
        + 'CRE: %{customdata[6]}<br>'
        + 'Part. efetivos: %{customdata[1]}<br>'
        + 'Concluintes: %{customdata[2]}<br>'
        + 'Tx: %{customdata[3]}<extra></extra>',
    });

    Plotly.react('g_esc_hist', traces, {
      ...BL,
      height: 300,
      showlegend: true,
      hovermode: 'closest',
      legend: { orientation: 'h', y: -0.22, font: { size: 10 } },
      margin: { l: 42, r: 12, t: 10, b: 44 },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)', range: [2023.9, 2025.1] },
      yaxis: {
        title: { text: 'nota', font: { size: 10 } },
        gridcolor: 'rgba(0,0,0,0)',
        range: [Math.min(...vals) - 6, Math.max(...vals) + 6],
      },
    }, CFG);

    const zeroLbl = zeroMode === 'no_zero'
      ? 'Filtro ativo: excluindo participantes com alguma nota zero.'
      : 'Filtro ativo: incluindo todos os participantes efetivos.';
    const lastPos = histYears.length - 1;
    const lastIdx = histIdx[lastPos];
    const partLast = series.part?.[lastIdx] || 0;
    const conclLast = school.concl?.[lastIdx] || 0;
    const txLast = series.tx?.[lastIdx];
    title.textContent = `${school.nome} · histórico 2024–${LAST_YEAR}`;
    note.innerHTML = `${zeroLbl} <b>${LAST_YEAR}:</b> ${NF(partLast)} part. efetivos`
      + `${conclLast ? ` · ${NF(conclLast)} concluintes` : ''}`
      + `${txLast != null ? ` · taxa ${txLast.toFixed(1)}%` : ''}`
      + `${school.obs ? ` · ${school.obs}` : ''}`;
  }

  function renderMun(creName, muns) {
    const ctx = _ctx;
    const { C, BL, CFG, NF, LAST_YEAR, LAST_INDEX, MS_GERAL_2024 } = ctx;
    const MS_AREA_2024 = _getRefArea2024();
    document.getElementById('munTitle').childNodes[0].nodeValue = `Munic\u00edpios de ${creName} \u00b7 participa\u00e7\u00e3o \u00d7 desempenho (${LAST_YEAR}) `;
    document.getElementById('munAttTitle').childNodes[0].nodeValue = `Aten\u00e7\u00e3o por \u00e1rea \u00b7 munic\u00edpios de ${creName} (${LAST_YEAR}) `;
    const xs = [];
    const ys = [];
    const sz = [];
    const tt = [];
    const col = [];
    const cd = [];
    const semtx = [];
    muns.forEach((m) => {
      const g = m.med[LAST_INDEX];
      const t = m.tx[LAST_INDEX];
      const c = m.concl || 30;
      if (t == null) { semtx.push(m.nome); return; }
      xs.push(t);
      ys.push(g);
      sz.push(Math.max(8, Math.sqrt(c) * 1.6));
      col.push(g < MS_GERAL_2024 && t < 27 ? C.critico : C.azul);
      tt.push(m.nome);
      cd.push([m.nome, NF(m.n && m.n[LAST_INDEX]), NF(m.concl)]);
    });
    const xmin = xs.length ? Math.min(...xs) : 0;
    const xmax = xs.length ? Math.max(...xs) : 60;
    const ymin = ys.length ? Math.min(...ys) : 470;
    const ymax = ys.length ? Math.max(...ys) : 520;
    const singleWithoutTx = xs.length === 0 && muns.length === 1 && semtx.length === 1;
    const munPlot = singleWithoutTx
      ? {
        traces: [{
          x: [muns[0].nome], y: [muns[0].med[LAST_INDEX]], text: [muns[0].nome], customdata: [[muns[0].nome, NF(muns[0].n && muns[0].n[LAST_INDEX]), NF(muns[0].concl)]],
          mode: 'markers+text', type: 'scatter', textposition: 'top center', textfont: { size: 9, color: C.muted },
          marker: { size: 18, color: C.azul, opacity: 0.78, line: { color: '#fff', width: 1 } },
          hovertemplate: '<b>%{text}</b><br>Taxa de participa\u00e7\u00e3o: indispon\u00edvel<br>%{customdata[1]} part. efetivos<br>M\u00e9dia: %{y:.1f}<extra></extra>',
        }],
        layout: {
          ...BL, height: 300, showlegend: false,
          xaxis: { title: { text: 'munic\u00edpio (taxa indispon\u00edvel)', font: { size: 10 } }, type: 'category', gridcolor: 'rgba(0,0,0,0)' },
          yaxis: { title: { text: 'm\u00e9dia geral', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
          shapes: [
            { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: MS_GERAL_2024, y1: MS_GERAL_2024, line: { color: C.brasil, width: 1, dash: 'dash' } },
          ],
        },
      }
      : {
        traces: [{
          x: xs, y: ys, text: tt, customdata: cd,
          mode: 'markers+text', type: 'scatter', textposition: 'top center', textfont: { size: 9, color: C.muted },
          marker: { size: sz, color: col, opacity: 0.7, line: { color: '#fff', width: 1 } },
          hovertemplate: '<b>%{text}</b><br>Part.: %{x:.1f}% \u00b7 %{customdata[1]} part. efetivos<br>M\u00e9dia: %{y:.1f}<br>Concluintes: %{customdata[2]}<extra></extra>',
        }],
        layout: {
          ...BL, height: 300, showlegend: false,
          xaxis: { title: { text: 'participa\u00e7\u00e3o efetiva (%)', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
          yaxis: { title: { text: 'm\u00e9dia geral', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
          shapes: [
            { type: 'line', x0: 27, x1: 27, y0: ymin - 5, y1: ymax + 5, line: { color: C.borda, width: 1, dash: 'dot' } },
            { type: 'line', x0: xmin - 3, x1: xmax + 3, y0: MS_GERAL_2024, y1: MS_GERAL_2024, line: { color: C.brasil, width: 1, dash: 'dash' } },
          ],
        },
      };
    Plotly.react('g_mun', munPlot.traces, munPlot.layout, CFG).then((gd) => {
      if (gd.removeAllListeners) gd.removeAllListeners('plotly_click');
      gd.on('plotly_click', (e) => { selectMun(e.points[0].customdata[0]); });
    });
    const nn = document.getElementById('munNota');
    nn.innerHTML = semtx.length
      ? `<b>Sem taxa de participa\u00e7\u00e3o (${semtx.length}):</b> ${semtx.join(', ')} \u2014 sem registro de concluintes na base municipal.${singleWithoutTx ? ' Como esta CRE possui apenas um munic\u00edpio, ele \u00e9 exibido acima apenas pelo desempenho.' : ' Eles continuam no mapa de aten\u00e7\u00e3o por \u00e1rea abaixo (que usa apenas o desempenho).'}`
      : '';
    const A4 = ['CN', 'CH', 'LC', 'MT', 'RED'];
    const porArea = ED.getPopulationMode ? ED.getPopulationMode() === 'por_area' : false;
    const rows = muns.map((m) => {
      const munPaData = porArea ? (ctx.DATA.munPorArea?.[m.nome]?.a2024 || {}) : {};
      return {
        n: m.nome,
        z: A4.map((k) => {
          const val = porArea && munPaData[k] != null ? munPaData[k] : m.a2024[k];
          return val == null ? null : Math.round(val - MS_AREA_2024[k]);
        }),
      };
    });
    rows.sort((a, b) => a.z.reduce((s, v) => s + (v || 0), 0) - b.z.reduce((s, v) => s + (v || 0), 0));
    Plotly.react('g_munheat', [{
      z: rows.map((r) => r.z), x: A4, y: rows.map((r) => r.n), type: 'heatmap',
      colorscale: [[0, '#B23A36'], [0.5, '#F2F4F7'], [1, '#1E7A4D']],
      zmid: 0, zmin: -30, zmax: 30,
      text: rows.map((r) => r.z), texttemplate: '%{text}', textfont: { size: 9 },
      colorbar: { thickness: 9, len: 0.8, tickfont: { size: 8 } },
      hovertemplate: '%{y} \u00b7 %{x}: %{z}<extra></extra>',
    }], {
      ...BL, height: 300, margin: { l: 120, r: 8, t: 6, b: 22 },
      xaxis: { side: 'top', tickfont: { size: 10 } },
      yaxis: { tickfont: { size: 8.5 }, autorange: 'reversed' },
    }, CFG);
  }

  function _getCreAreas(name) {
    const { DATA } = _ctx;
    const porArea = ED.getPopulationMode ? ED.getPopulationMode() === 'por_area' : false;
    if (porArea && DATA.crePorArea?.[name]?.areas) {
      return DATA.crePorArea[name].areas;
    }
    return DATA.cre[name].areas;
  }

  function _getRefArea2024() {
    const { DATA, MS_AREA_2024 } = _ctx;
    const porArea = ED.getPopulationMode ? ED.getPopulationMode() === 'por_area' : false;
    return (porArea ? DATA.msArea2024PorArea : null) || MS_AREA_2024;
  }

  function selectCre(name, opts = {}) {
    const ctx = _ctx;
    const { DATA, LAST_YEAR } = ctx;
    const shouldScroll = opts.scroll !== false;
    SEL_CRE = name;
    SEL_MUN = null;
    SEL_ESC = null;
    document.querySelectorAll('.ctile').forEach((t) =>
      t.classList.toggle('sel', t.querySelector('.ct span').textContent === name)
    );
    document.getElementById('escCard').style.display = 'none';
    document.getElementById('creAreaCard').style.display = 'block';
    document.querySelector('#creAreaTitle span').textContent = `${name} \u00b7 ${ctx.ANOS[0]}\u2013${LAST_YEAR}`;
    renderAreas('creAreas', _getCreAreas(name), _getRefArea2024());
    const muns = (DATA.creMuns[name] || [])
      .map((m) => (DATA.mun[m] ? { nome: m, ...DATA.mun[m] } : null))
      .filter(Boolean);
    document.getElementById('munRow').style.display = muns.length ? 'grid' : 'none';
    renderMun(name, muns);
    bread();
    if (shouldScroll) {
      document.getElementById('munRow').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function _getMunAreas(name) {
    const { DATA } = _ctx;
    const porArea = ED.getPopulationMode ? ED.getPopulationMode() === 'por_area' : false;
    if (porArea && DATA.munPorArea?.[name]?.areas) {
      return DATA.munPorArea[name].areas;
    }
    return DATA.mun[name]?.areas || {};
  }

  function selectMun(name) {
    const ctx = _ctx;
    const { DATA, LAST_YEAR, MS_AREA_2024, MS_GERAL_2024, MS_AREA_2024_SEM_ZERO, MS_GERAL_2024_SEM_ZERO } = ctx;
    SEL_MUN = name;
    bread();
    document.querySelector('#creAreaTitle span').textContent = `${name} \u00b7 ${ctx.ANOS[0]}\u2013${LAST_YEAR}`;
    if (DATA.mun[name]) renderAreas('creAreas', _getMunAreas(name), _getRefArea2024());
    const zeroMode = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    const refArea = zeroMode === 'no_zero' && Object.keys(MS_AREA_2024_SEM_ZERO || {}).length
      ? MS_AREA_2024_SEM_ZERO
      : MS_AREA_2024;
    const refGeral = zeroMode === 'no_zero' && MS_GERAL_2024_SEM_ZERO != null
      ? MS_GERAL_2024_SEM_ZERO
      : MS_GERAL_2024;
    const list = (DATA.esc[name] || [])
      .map((s) => {
        if (zeroMode !== 'no_zero') return s;
        const nz = s.semZero || {};
        return {
          ...s,
          part: nz.part ?? 0,
          tx: nz.tx ?? null,
          cn: nz.cn ?? null,
          ch: nz.ch ?? null,
          lc: nz.lc ?? null,
          mt: nz.mt ?? null,
          red: nz.red ?? null,
          geral: nz.geral ?? null,
        };
      })
      .filter((s) => s.geral != null && (s.part || 0) >= 10)
      .sort((a, b) => a.geral - b.geral);
    document.getElementById('escCard').style.display = list.length ? 'block' : 'none';
    document.getElementById('escTitle').childNodes[0].nodeValue = `Escolas de ${name} \u00b7 ${LAST_YEAR} `;
    const body = document.getElementById('escBody');
    body.innerHTML = '';
    const cell = (v, k) => {
      const ref = refArea[k];
      const cls = ref != null && v < ref ? 'bad' : (ref != null && v >= ref + 8 ? 'ok' : '');
      return `<td class="${cls}">${v.toFixed(0)}</td>`;
    };
    list.forEach((s) => {
      const tr = document.createElement('tr');
      tr.dataset.schoolId = s.id || '';
      tr.innerHTML = `<td>${s.nome}</td><td>${s.concl != null ? s.concl : '<span class="muted">\u2014</span>'}</td><td>${s.part}</td><td>${s.tx != null ? `${s.tx.toFixed(0)}%` : '<span class="muted">\u2014</span>'}</td>`
        + cell(s.cn, 'CN') + cell(s.ch, 'CH') + cell(s.lc, 'LC') + cell(s.mt, 'MT') + cell(s.red, 'RED')
        + `<td class="b${refGeral != null && s.geral < refGeral ? ' bad' : ''}">${s.geral.toFixed(0)}</td>`;
      tr.onclick = () => {
        SEL_ESC = s.id || null;
        setSelectedSchoolRow(SEL_ESC);
        renderSchoolHistory(name, SEL_ESC);
      };
      body.appendChild(tr);
    });
    SEL_ESC = list.some((s) => s.id === SEL_ESC) ? SEL_ESC : (list[0]?.id || null);
    setSelectedSchoolRow(SEL_ESC);
    renderSchoolHistory(name, SEL_ESC);
    document.getElementById('escCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function resetDrill() {
    SEL_CRE = null;
    SEL_MUN = null;
    SEL_ESC = null;
    document.querySelectorAll('.ctile').forEach((t) => t.classList.remove('sel'));
    ['creAreaCard', 'munRow', 'escCard'].forEach((id) => {
      document.getElementById(id).style.display = 'none';
    });
    bread();
  }

  ED.initDrill = function (ctx) {
    _ctx = ctx;
    const { DATA, ANOS, LAST_INDEX, LAST_YEAR, C, BL, CFG, NF, norm } = ctx;
    document.querySelectorAll('[data-school-zero-mode]').forEach((el) => {
      if (el.dataset.zeroModeBound === '1') return;
      el.dataset.zeroModeBound = '1';
      el.onchange = () => {
        if (ED.setSchoolZeroMode) ED.setSchoolZeroMode(el.value);
      };
    });
    document.addEventListener('enemdash:schoolZeroMode', () => {
      if (SEL_MUN) selectMun(SEL_MUN);
    });
    document.addEventListener('enemdash:populationMode', () => {
      if (SEL_MUN) selectMun(SEL_MUN);
      else if (SEL_CRE) selectCre(SEL_CRE, { scroll: false });
    });
    const row = document.getElementById('creRow');
    function creTrajData(o) {
      const xs = [];
      const ys = [];
      const cd = [];
      ANOS.forEach((a, i) => {
        const tx = o.tx?.[i];
        const med = o.med?.[i];
        if (tx == null || med == null || Number.isNaN(tx) || Number.isNaN(med)) return;
        xs.push(tx);
        ys.push(med);
        cd.push([a, NF(o.n && o.n[i])]);
      });
      return { xs, ys, cd };
    }

    function creTrajRanges(o) {
      const { xs, ys } = creTrajData(o);
      const padX = (v) => Math.max(2, v * 0.15);
      const padY = 4;
      const xMin = xs.length ? Math.min(...xs) : 0;
      const xMax = xs.length ? Math.max(...xs) : 60;
      const yMin = ys.length ? Math.min(...ys) : 460;
      const yMax = ys.length ? Math.max(...ys) : 535;
      return {
        x: [Math.max(0, xMin - padX(xMin)), xMax + padX(xMax)],
        y: [yMin - padY, yMax + padY],
      };
    }

    Object.keys(DATA.cre || {}).forEach((name) => {
      const o = DATA.cre[name];
      const adv = o.med[LAST_INDEX] >= o.med[0];
      const sid = `ct_${norm(name).replace(/ /g, '_')}`;
      const t = document.createElement('div');
      t.className = 'ctile';
      t.onclick = () => selectCre(name);
      t.innerHTML = `<div class="ct"><span>${name}</span><span class="arr" style="color:${adv ? C.verde : C.critico}">${adv ? '\u25B2' : '\u25BC'}</span></div><div id="${sid}" style="height:78px"></div>`;
      row.appendChild(t);
      const traj = creTrajData(o);
      const rng = creTrajRanges(o);
      const traces = [];
      if (traj.xs.length >= 2) {
        traces.push({
          x: traj.xs, y: traj.ys, customdata: traj.cd, mode: 'lines',
          line: { color: 'rgba(10,77,140,.55)', width: 2 },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<br>Part. efetivos: %{customdata[1]}<extra></extra>',
        });
        traces.push({
          x: [traj.xs[0]], y: [traj.ys[0]], customdata: [traj.cd[0]], mode: 'markers',
          marker: { color: C.borda, size: 6 },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        const li = traj.xs.length - 1;
        traces.push({
          x: [traj.xs[li]], y: [traj.ys[li]], customdata: [traj.cd[li]], mode: 'markers',
          marker: { color: adv ? C.verde : C.critico, size: 8, line: { color: '#fff', width: 1 } },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
      } else {
        const medPts = (o.med || []).filter((v) => v != null && !Number.isNaN(v));
        rng.y = medPts.length
          ? [Math.min(...medPts) - 4, Math.max(...medPts) + 4]
          : [460, 535];
        delete rng.x;
        traces.push({
          x: ANOS.map(String), y: o.med, mode: 'lines+markers',
          line: { color: 'rgba(10,77,140,.55)', width: 2 },
          marker: { size: 4, color: C.azul },
          hovertemplate: '<b>%{x}</b><br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        traces.push({
          x: [String(ANOS[0])], y: [o.med[0]], mode: 'markers', marker: { color: C.borda, size: 6 },
          hovertemplate: '<b>2019</b><br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        traces.push({
          x: [String(ANOS[LAST_INDEX])], y: [o.med[LAST_INDEX]], mode: 'markers',
          marker: { color: adv ? C.verde : C.critico, size: 8, line: { color: '#fff', width: 1 } },
          hovertemplate: `<b>${LAST_YEAR}</b><br>M\u00e9dia: %{y:.0f}<extra></extra>`,
        });
      }
      const xaxis = rng.x
        ? { visible: false, range: rng.x }
        : { visible: false, type: 'category', categoryorder: 'array', categoryarray: ANOS.map(String) };
      Plotly.newPlot(sid, traces, {
        ...BL, height: 78, margin: { l: 4, r: 6, t: 4, b: 4 },
        showlegend: false, hovermode: 'closest',
        xaxis,
        yaxis: { visible: false, range: rng.y },
      }, CFG);
    });
    bread();
    if (DATA.cre && DATA.cre['CRE SED']) {
      selectCre('CRE SED', { scroll: false });
    }
    if (ED.setSchoolZeroMode) ED.setSchoolZeroMode(ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all');
    window.selectCre = selectCre;
    window.selectMun = selectMun;
    window.resetDrill = resetDrill;
  };
})(window.EnemDash);
