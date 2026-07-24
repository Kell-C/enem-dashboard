(function (ED) {
  let SEL_CRE = null;
  let SEL_MUN = null;
  let SEL_ESC = null;
  let _ctx = null;

  function bread() {
    const b = document.getElementById('bread');
    let h = `<span class="crumb ${SEL_CRE ? '' : 'active'}" onclick="resetDrill()">Estado \u00b7 MS</span>`;
    if (SEL_CRE) {
      h += `<span class="sepc">\u2192</span><span class="crumb ${SEL_MUN ? '' : 'active'}" onclick="selectCre('${SEL_CRE.replace(/'/g, "\\'")}')">${ED.creDisplay(SEL_CRE)}</span>`;
    }
    if (SEL_MUN) {
      h += `<span class="sepc">\u2192</span><span class="crumb active">${SEL_MUN}</span>`;
    }
    b.innerHTML = h;
  }

  function fmtAreaNum(v) {
    return v == null || Number.isNaN(v) ? '—' : v.toFixed(1).replace('.', ',');
  }

  function areaTrendHtml(vLast, vPrev, prevYear) {
    if (vLast == null || vPrev == null || Number.isNaN(vLast) || Number.isNaN(vPrev)) {
      return `<span class="trend">— vs ${prevYear}</span>`;
    }
    const d = vLast - vPrev;
    if (d > 0.05) {
      return `<span class="trend up">\u25B2 +${fmtAreaNum(d)} vs ${prevYear}</span>`;
    }
    if (d < -0.05) {
      return `<span class="trend down">\u25BC ${fmtAreaNum(d)} vs ${prevYear}</span>`;
    }
    return `<span class="trend up">\u25B2 est\u00e1vel vs ${prevYear}</span>`;
  }

  function fmtDeltaPts(delta) {
    if (delta == null || Number.isNaN(delta)) return null;
    const n = Math.round(delta);
    return `${n >= 0 ? '+' : ''}${n}`;
  }

  function renderAreaKpis(areas, refMap, hostId = 'creAreaKpis', opts = {}) {
    const ctx = _ctx;
    const { LAST_INDEX, PREV_INDEX, PREV_YEAR, ACOR } = ctx;
    const { AREANOME_FULL } = ED.Config;
    const host = document.getElementById(hostId);
    if (!host) return;
    if (!areas) {
      host.innerHTML = '';
      return;
    }
    const compareAreas = opts.compareAreas || null;
    const compareLabel = opts.compareLabel || 'CRE';
    const refBrMap = opts.refBrMap || null;
    host.innerHTML = ctx.AREAKEYS.map((k) => {
      const name = AREANOME_FULL[k] || k;
      const v25 = areas[k]?.[LAST_INDEX];
      const v24 = areas[k]?.[PREV_INDEX];
      const refMs = refMap?.[k];
      const warnMs = v25 != null && refMs != null && v25 < refMs;
      const deltaMs = v25 != null && refMs != null ? v25 - refMs : null;
      const refBr = refBrMap?.[k];
      const deltaBr = v25 != null && refBr != null ? v25 - refBr : null;
      const warnBr = deltaBr != null && deltaBr < 0;
      const refCmp = compareAreas?.[k]?.[LAST_INDEX] ?? compareAreas?.[k] ?? null;
      const deltaCmp = v25 != null && refCmp != null ? v25 - refCmp : null;
      const warnCmp = deltaCmp != null && deltaCmp < 0;
      const cmpHtml = compareAreas
        ? (deltaCmp == null
          ? `<span class="kpi-delta kpi-delta-territory">— vs ${compareLabel}</span>`
          : `<span class="kpi-delta kpi-delta-territory ${warnCmp ? 'below' : 'above'}">${fmtDeltaPts(deltaCmp)} vs ${compareLabel}</span>`)
        : '';
      const msHtml = deltaMs == null
        ? '<span class="kpi-delta kpi-delta-ms" title="Média MS · escolas estaduais (concluintes, não eliminados)">— vs MS</span>'
        : `<span class="kpi-delta kpi-delta-ms ${warnMs ? 'below' : 'above'}" title="Média MS · escolas estaduais (concluintes, não eliminados)">${fmtDeltaPts(deltaMs)} vs MS</span>`;
      const brHtml = refBrMap
        ? (deltaBr == null
          ? '<span class="kpi-delta kpi-delta-ms kpi-delta-br" title="Média Brasil · escolas estaduais (concluintes, não eliminados)">— vs BR</span>'
          : `<span class="kpi-delta kpi-delta-ms kpi-delta-br ${warnBr ? 'below' : 'above'}" title="Média Brasil · escolas estaduais (concluintes, não eliminados)">${fmtDeltaPts(deltaBr)} vs BR</span>`)
        : '';
      const secondary = [compareAreas ? msHtml : '', brHtml].filter(Boolean)
        .map((html) => `<div class="vsub vsub-ms">${html}</div>`).join('');
      return `<div class="kpi kpi-area rank-area-kpi${warnMs ? ' warn' : ''}${warnCmp ? ' warn-cre' : ''}" data-area="${k}" style="--area-accent:${ACOR[k]}">
        <div class="kpi-area-bar" aria-hidden="true"></div>
        <div class="kpi-area-head">
          <p class="lbl">${name}</p>
          ${cmpHtml || msHtml}
        </div>
        <div class="val" style="color:${ACOR[k]}">${fmtAreaNum(v25)}</div>
        <div class="vsub">${areaTrendHtml(v25, v24, PREV_YEAR)}</div>
        ${secondary}
      </div>`;
    }).join('');
  }

  function territoryCmpFlags(v, munRef, creRef) {
    const bits = [];
    if (v != null && munRef != null && !Number.isNaN(munRef)) {
      const above = v >= munRef;
      bits.push(`<span class="cmp-flag ${above ? 'above' : 'below'}" title="${above ? 'Igual ou acima' : 'Abaixo'} da m\u00e9dia do munic\u00edpio">Mun ${above ? '\u25B2' : '\u25BC'}</span>`);
    }
    if (v != null && creRef != null && !Number.isNaN(creRef)) {
      const above = v >= creRef;
      bits.push(`<span class="cmp-flag ${above ? 'above' : 'below'}" title="${above ? 'Igual ou acima' : 'Abaixo'} da m\u00e9dia da CRE">CRE ${above ? '\u25B2' : '\u25BC'}</span>`);
    }
    return bits.length ? `<div class="cmp-flags">${bits.join('')}</div>` : '';
  }

  function renderCombinedAreaChart(areas, label, opts = {}) {
    const ctx = _ctx;
    const { ANOS, AREAKEYS, AREANOME, ACOR, BL, CFG, LAST_YEAR } = ctx;
    const plotId = opts.plotId || 'g_mun_areas';
    const wrapId = opts.wrapId || 'munDetailCard';
    const titleId = opts.titleId || 'munTrajAreasTitle';
    const uirevision = opts.uirevision || 'drill-areas';
    const wrap = document.getElementById(wrapId);
    const title = document.getElementById(titleId);
    const el = document.getElementById(plotId);
    if (!el || !areas) return;
    if (wrap && opts.showWrap !== false) wrap.style.display = 'block';
    if (title) {
      if (title.tagName === 'H3' && title.querySelector('span')) {
        title.querySelector('span').textContent = `${label} \u00b7 ${ANOS[0]}\u2013${LAST_YEAR}`;
      } else {
        title.textContent = `Trajet\u00f3ria das m\u00e9dias por \u00e1rea \u00b7 ${label} \u00b7 ${ANOS[0]}\u2013${LAST_YEAR}`;
      }
    }
    const mergeP = ED.Config.mergePandemia;
    const hoverScore = ED.Config.hoverAreaScore || ED.Config.hoverAreaTemplate;
    const yLo = 0;
    const yHi = 1000;
    const tr = AREAKEYS.map((k) => {
      const ys = areas[k] || [];
      const arrows = ED.segmentArrowsFromSeries(ANOS, ys, {
        color: ACOR[k],
        arrowsize: 0.55,
        arrowwidth: 1.1,
        standoff: 2,
        startstandoff: 2,
      });
      const nome = (ED.Config.AREANOME_FULL && ED.Config.AREANOME_FULL[k]) || AREANOME[k];
      return {
        x: ANOS,
        y: ys,
        mode: 'lines',
        name: nome,
        line: { color: ACOR[k], width: 2.2 },
        hovertemplate: hoverScore(nome, 0),
        _arrows: arrows,
      };
    });
    const areaArrows = tr.flatMap((t) => t._arrows || []);
    tr.forEach((t) => { delete t._arrows; });
    Plotly.react(el, tr, mergeP({
      ...BL, height: 300, dragmode: false, hovermode: 'x unified', uirevision,
      legend: { orientation: 'h', y: -0.22, font: { size: 9.5 } },
      xaxis: { dtick: 1, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: {
        title: { text: 'm\u00e9dia (pontos)', font: { size: 10 } },
        gridcolor: 'rgba(0,0,0,0)',
        range: [yLo, yHi],
        dtick: 200,
      },
      annotations: areaArrows,
    }, { y0: yLo, y1: yHi }), CFG);
  }

  function hideMunDetailCard() {
    const card = document.getElementById('munDetailCard');
    if (card) card.style.display = 'none';
    const kpis = document.getElementById('munAreaKpis');
    if (kpis) kpis.innerHTML = '';
  }

  function hideCreTrajAreasChart() {
    const card = document.getElementById('creTrajAreasCard');
    if (card) card.style.display = 'none';
  }

  function renderAreas(containerId, areas, refMap) {
    const ctx = _ctx;
    const { ANOS, DATA, AREANOME, ACOR, C, BL, CFG } = ctx;
    const host = document.getElementById(containerId);
    const hoverScore = ED.Config.hoverAreaScore || ED.Config.hoverAreaTemplate;
    host.innerHTML = '';
    ctx.AREAKEYS.forEach((k) => {
      const v = areas[k];
      const last = v[v.length - 1];
      const ref = refMap[k];
      const brSeries = DATA.msArea?.[k]?.br || [];
      const brLast = brSeries[brSeries.length - 1];
      const warn = last != null && ref != null && last < ref;
      const tile = document.createElement('div');
      tile.className = `atile${warn ? ' warn' : ''}`;
      const deltaMs = last != null && ref != null ? last - ref : null;
      const deltaBr = last != null && brLast != null ? last - brLast : null;
      const msTxt = deltaMs == null ? '—' : `${deltaMs >= 0 ? '+' : ''}${deltaMs.toFixed(0)}`;
      const brTxt = deltaBr == null ? '—' : `${deltaBr >= 0 ? '+' : ''}${deltaBr.toFixed(0)}`;
      tile.innerHTML = `<div class="at"><span>${k}</span><span class="fl" style="color:${warn ? C.critico : C.verde}" title="vs MS (esc. estaduais)">${msTxt}<span class="fl-br" title="vs BR (esc. estaduais)"> · ${brTxt}</span></span></div><div id="${containerId}_${k}" style="height:74px"></div>`;
      host.appendChild(tile);
      Plotly.newPlot(`${containerId}_${k}`, [
        {
          x: ANOS, y: brSeries, mode: 'lines', name: `${AREANOME[k]} · BR`,
          line: { color: '#B7C0CC', width: 1.15, dash: 'dash' },
          hovertemplate: hoverScore(`${AREANOME[k]} · BR`, '%{y:.0f}'),
        },
        {
          x: ANOS, y: DATA.msArea[k].ms, mode: 'lines', name: `${AREANOME[k]} · MS`,
          line: { color: C.brasil, width: 1.4, dash: 'dot' },
          hovertemplate: hoverScore(`${AREANOME[k]} · MS`, '%{y:.0f}'),
        },
        {
          x: ANOS, y: v, mode: 'lines', name: AREANOME[k],
          line: { color: ACOR[k], width: 2 },
          hovertemplate: hoverScore(AREANOME[k], '%{y:.0f}'),
        },
      ], ED.withPandemia({
        ...BL, height: 74, margin: { l: 4, r: 6, t: 4, b: 14 },
        showlegend: false, xaxis: { visible: false }, yaxis: { visible: false },
      }, { anos: ANOS, annotate: false }), CFG);
    });
  }

  function brAreaRefs(ctx, zeroMode) {
    const { DATA, AREAKEYS, LAST_INDEX, MED_BR, MED_BR_SEM_ZERO } = ctx;
    const src = zeroMode === 'no_zero' ? (DATA.msAreaSemZero || DATA.msArea) : DATA.msArea;
    const areas = {};
    AREAKEYS.forEach((k) => {
      const br = src?.[k]?.br;
      areas[k] = br?.[LAST_INDEX] ?? null;
    });
    const brGeral = zeroMode === 'no_zero' ? MED_BR_SEM_ZERO[LAST_INDEX] : MED_BR[LAST_INDEX];
    return { areas, geral: brGeral ?? null };
  }

  function scoreCellClass(v, refMs, refBr) {
    if (v == null || refMs == null) return '';
    if (refBr != null && v >= refBr) return 'br-ok';
    if (v >= refMs) return 'ms-ok';
    return 'bad';
  }

  function setSelectedSchoolRow(schoolId) {
    document.querySelectorAll('#escBody tr').forEach((tr) => {
      tr.classList.toggle('is-sel', tr.dataset.schoolId === schoolId);
    });
  }

  function rankingHistorico(schoolId) {
    const list = window.RANKING_ESCOLAS_2025?.escolas;
    if (!list) return null;
    const esc = list.find((e) => String(e.coInep) === String(schoolId));
    const h = esc?.historico;
    return h?.anos?.length ? h : null;
  }

  function escHistYearsWithData(anos, school, series, areaKeys) {
    return anos.filter((ano) => {
      const idx = anos.indexOf(ano);
      if ((series.geral || school.geral || [])[idx] != null) return true;
      return areaKeys.some((k) => (series.areas?.[k] || [])[idx] != null);
    });
  }

  function renderSchoolHistory(munName, schoolId) {
    const ctx = _ctx;
    const { DATA, ANOS, LAST_YEAR, AREANOME, ACOR, BL, CFG, NF } = ctx;
    const {
      C, layoutLineChart, hoverAreaTemplate, mergePandemia, AREANOME_FULL,
    } = ED.Config;
    const axisMuted = C.txt2 || C.muted;
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
    const rankHist = zeroMode === 'all' ? rankingHistorico(schoolId) : null;
    let histYears;
    let geral;
    let areasByYear;
    let histIdx = null;

    if (rankHist) {
      histYears = rankHist.anos.slice();
      geral = rankHist.media.slice();
      areasByYear = {};
      ctx.AREAKEYS.forEach((k) => {
        areasByYear[k] = rankHist[k] ? rankHist[k].slice() : histYears.map(() => null);
      });
    } else {
      const series = zeroMode === 'no_zero' ? (school.semZero || {}) : school;
      histYears = escHistYearsWithData(ANOS, school, series, ctx.AREAKEYS);
      histIdx = histYears.map((ano) => ANOS.indexOf(ano)).filter((idx) => idx >= 0);
      geral = histIdx.map((idx) => (series.geral || school.geral || [])[idx] ?? null);
      areasByYear = {};
      ctx.AREAKEYS.forEach((k) => {
        areasByYear[k] = histIdx.map((idx) => (series.areas?.[k] || [])[idx] ?? null);
      });
    }

    const vals = [];
    ctx.AREAKEYS.forEach((k) => {
      areasByYear[k].forEach((v) => { if (v != null) vals.push(v); });
    });
    geral.forEach((v) => { if (v != null) vals.push(v); });
    if (!vals.length) {
      title.textContent = `${school.nome} · histórico`;
      note.textContent = 'Sem série histórica suficiente com o filtro atual.';
      host.innerHTML = '<p class="idx-empty">Sem dados históricos para exibir com os parâmetros atuais.</p>';
      return;
    }

    const seriesMeta = zeroMode === 'no_zero' ? (school.semZero || {}) : school;
    const legendKeys = ['LC', 'CH', 'CN', 'MT', 'RED'].filter((k) => ctx.AREAKEYS.includes(k));

    const traces = legendKeys.map((k) => {
      const name = AREANOME_FULL[k] || AREANOME[k];
      return {
        x: histYears,
        y: areasByYear[k],
        mode: 'lines',
        name,
        line: { color: ACOR[k], width: 2.5 },
        connectgaps: false,
        hovertemplate: hoverAreaTemplate(name),
      };
    });
    traces.push({
      x: histYears,
      y: geral,
      mode: 'lines',
      name: 'Média geral',
      line: { color: C.brasil, width: 2, dash: 'dot' },
      connectgaps: false,
      hovertemplate: hoverAreaTemplate('Média geral'),
    });

    const anoMin = Math.min(...histYears);
    const anoMax = Math.max(...histYears);

    Plotly.react('g_esc_hist', traces, mergePandemia(layoutLineChart({
      height: 340,
      margin: { l: 36, r: 20, t: 16, b: 44 },
      showlegend: true,
      legend: { orientation: 'h', y: 1.18, x: 0, font: { size: 11, color: axisMuted } },
      xaxis: {
        title: '',
        dtick: histYears.length > 8 ? 2 : 1,
        tickmode: 'linear',
        range: [anoMin - 0.5, anoMax + 0.5],
        gridcolor: 'rgba(0,0,0,0)',
        showgrid: false,
        linecolor: '#E5E7EF',
        tickfont: { size: 12, color: axisMuted },
      },
      yaxis: {
        title: { text: 'Nota TRI', font: { size: 9, color: axisMuted } },
        range: [0, 1000],
        dtick: 200,
        gridcolor: 'rgba(0,0,0,0)',
        showgrid: false,
        linecolor: '#E5E7EF',
        tickfont: { size: 8, color: axisMuted },
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: '#FFFFFF',
    }), { y0: 0, y1: 1000 }), CFG);

    const zeroLbl = zeroMode === 'no_zero'
      ? 'Filtro ativo: excluindo participantes com alguma nota zero.'
      : 'Filtro ativo: incluindo todos os participantes efetivos.';
    const lastPos = histYears.length - 1;
    const lastAno = histYears[lastPos];
    const lastIdx = ANOS.indexOf(lastAno);
    const partLast = lastIdx >= 0 ? (seriesMeta.part?.[lastIdx] || 0) : 0;
    const conclLast = lastIdx >= 0 ? (school.concl?.[lastIdx] || 0) : 0;
    const txLast = lastIdx >= 0 ? seriesMeta.tx?.[lastIdx] : null;
    const rangeLbl = anoMin === anoMax ? String(anoMax) : `${anoMin}–${anoMax}`;
    const fonteLbl = rankHist ? ' · série histórica 2013–2025' : '';
    title.textContent = `${school.nome} · histórico ${rangeLbl}`;
    note.innerHTML = `${zeroLbl}${fonteLbl}${lastIdx >= 0 ? ` <b>${lastAno}:</b> ${NF(partLast)} part. efetivos`
      + `${conclLast ? ` · ${NF(conclLast)} concluintes` : ''}`
      + `${txLast != null ? ` · taxa ${txLast.toFixed(1)}%` : ''}` : ''}`
      + `${school.obs ? ` · ${school.obs}` : ''}`;
  }

  function renderMun(creName, muns) {
    const ctx = _ctx;
    const { C, BL, CFG, NF, LAST_YEAR, LAST_INDEX, MS_GERAL_2024, MS_AREA_2024 } = ctx;
    const creLbl = ED.creDisplay(creName);
    document.getElementById('munTitle').childNodes[0].nodeValue = `Munic\u00edpios de ${creLbl} \u00b7 participa\u00e7\u00e3o \u00d7 desempenho (${LAST_YEAR}) `;
    document.getElementById('munAttTitle').childNodes[0].nodeValue = `Aten\u00e7\u00e3o por \u00e1rea \u00b7 munic\u00edpios de ${creLbl} (${LAST_YEAR}) `;
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
    const rows = muns.map((m) => ({
      n: m.nome,
      z: A4.map((k) => {
        const val = m.a2024[k];
        return val == null ? null : Math.round(val - MS_AREA_2024[k]);
      }),
    }));
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

  function selectCre(name, opts = {}) {
    const ctx = _ctx;
    const { DATA, LAST_YEAR, MS_AREA_2024 } = ctx;
    const shouldScroll = opts.scroll !== false;
    SEL_CRE = name;
    SEL_MUN = null;
    SEL_ESC = null;
    document.querySelectorAll('.ctile').forEach((t) =>
      t.classList.toggle('sel', t.querySelector('.ct span').textContent === ED.creDisplay(name))
    );
    document.getElementById('escCard').style.display = 'none';
    hideMunDetailCard();
    document.getElementById('creAreaCard').style.display = 'block';
    document.querySelector('#creAreaTitle span').textContent = `${ED.creDisplay(name)} \u00b7 ${ctx.ANOS[0]}\u2013${LAST_YEAR}`;
    document.getElementById('creAreas').style.display = 'grid';
    const creRefBr = brAreaRefs(ctx, ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all');
    renderAreaKpis(DATA.cre[name].areas, MS_AREA_2024, 'creAreaKpis', { refBrMap: creRefBr.areas });
    renderAreas('creAreas', DATA.cre[name].areas, MS_AREA_2024);
    const creTrajCard = document.getElementById('creTrajAreasCard');
    if (creTrajCard && DATA.cre[name]?.areas) {
      creTrajCard.style.display = 'block';
      renderCombinedAreaChart(DATA.cre[name].areas, ED.creDisplay(name), {
        plotId: 'g_cre_areas',
        wrapId: 'creTrajAreasCard',
        titleId: 'creTrajAreasTitle',
        uirevision: 'cre-traj-areas',
        showWrap: false,
      });
    } else if (creTrajCard) {
      creTrajCard.style.display = 'none';
    }
    const muns = (DATA.creMuns[name] || [])
      .map((m) => (DATA.mun[m] ? { nome: m, ...DATA.mun[m] } : null))
      .filter(Boolean);
    document.getElementById('munRow').style.display = muns.length ? 'grid' : 'none';
    renderMun(name, muns);
    bread();
    if (shouldScroll) {
      document.getElementById('munRow').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (ED.track) ED.track('cre_select', { cre: name });
  }

  function selectMun(name) {
    const ctx = _ctx;
    const {
      DATA, LAST_YEAR, LAST_INDEX, MS_AREA_2024, MS_GERAL_2024,
      MS_AREA_2024_SEM_ZERO, MS_GERAL_2024_SEM_ZERO,
    } = ctx;
    SEL_MUN = name;
    bread();

    if (SEL_CRE && DATA.cre[SEL_CRE]) {
      document.getElementById('creAreaCard').style.display = 'block';
      document.querySelector('#creAreaTitle span').textContent = `${ED.creDisplay(SEL_CRE)} \u00b7 ${ctx.ANOS[0]}\u2013${LAST_YEAR}`;
      document.getElementById('creAreas').style.display = 'grid';
      const creRefBrKeep = brAreaRefs(ctx, ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all');
      renderAreaKpis(DATA.cre[SEL_CRE].areas, MS_AREA_2024, 'creAreaKpis', { refBrMap: creRefBrKeep.areas });
      renderAreas('creAreas', DATA.cre[SEL_CRE].areas, MS_AREA_2024);
    }

    const munCard = document.getElementById('munDetailCard');
    if (munCard && DATA.mun[name]) {
      munCard.style.display = 'block';
      const titleSpan = document.querySelector('#munDetailTitle span');
      if (titleSpan) titleSpan.textContent = `${name} \u00b7 ${ctx.ANOS[0]}\u2013${LAST_YEAR}`;
      const creAreas = SEL_CRE && DATA.cre[SEL_CRE] ? DATA.cre[SEL_CRE].areas : null;
      const munRefBr = brAreaRefs(ctx, ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all');
      renderAreaKpis(DATA.mun[name].areas, MS_AREA_2024, 'munAreaKpis', {
        compareAreas: creAreas,
        compareLabel: 'CRE',
        refBrMap: munRefBr.areas,
      });
      renderCombinedAreaChart(DATA.mun[name].areas, name, {
        plotId: 'g_mun_areas',
        wrapId: 'munDetailCard',
        titleId: 'munTrajAreasTitle',
        uirevision: 'mun-traj-areas',
        showWrap: false,
      });
    } else {
      hideMunDetailCard();
    }

    const munMed = DATA.mun[name]?.med?.[LAST_INDEX] ?? null;
    const creMed = SEL_CRE && DATA.cre[SEL_CRE] ? (DATA.cre[SEL_CRE].med?.[LAST_INDEX] ?? null) : null;
    const munAreaRef = {};
    const creAreaRef = {};
    ctx.AREAKEYS.forEach((k) => {
      munAreaRef[k] = DATA.mun[name]?.areas?.[k]?.[LAST_INDEX] ?? null;
      creAreaRef[k] = SEL_CRE && DATA.cre[SEL_CRE]
        ? (DATA.cre[SEL_CRE].areas?.[k]?.[LAST_INDEX] ?? null)
        : null;
    });
    const zeroMode = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    const refArea = zeroMode === 'no_zero' && Object.keys(MS_AREA_2024_SEM_ZERO || {}).length
      ? MS_AREA_2024_SEM_ZERO
      : MS_AREA_2024;
    const refGeral = zeroMode === 'no_zero' && MS_GERAL_2024_SEM_ZERO != null
      ? MS_GERAL_2024_SEM_ZERO
      : MS_GERAL_2024;
    const refBr = brAreaRefs(ctx, zeroMode);
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
      const cls = scoreCellClass(v, refArea[k], refBr.areas[k]);
      return `<td class="score-cell ${cls}"><span class="score-val">${v.toFixed(0)}</span>${territoryCmpFlags(v, munAreaRef[k], creAreaRef[k])}</td>`;
    };
    list.forEach((s) => {
      const tr = document.createElement('tr');
      tr.dataset.schoolId = s.id || '';
      const belowMun = munMed != null && s.geral < munMed;
      if (belowMun) tr.classList.add('below-mun');
      tr.innerHTML = `<td>${s.nome}</td><td>${s.concl != null ? s.concl : '<span class="muted">\u2014</span>'}</td><td>${s.part}</td><td>${s.tx != null ? `${s.tx.toFixed(0)}%` : '<span class="muted">\u2014</span>'}</td>`
        + cell(s.cn, 'CN') + cell(s.ch, 'CH') + cell(s.lc, 'LC') + cell(s.mt, 'MT') + cell(s.red, 'RED')
        + `<td class="score-cell b ${scoreCellClass(s.geral, refGeral, refBr.geral)}"><span class="score-val">${s.geral.toFixed(0)}</span>${territoryCmpFlags(s.geral, munMed, creMed)}</td>`;
      tr.onclick = () => {
        SEL_ESC = s.id || null;
        setSelectedSchoolRow(SEL_ESC);
        renderSchoolHistory(name, SEL_ESC);
        if (ED.track) {
          ED.track('school_view', {
            inep: s.id || null,
            municipio: name,
            source: 'territorio',
          });
        }
      };
      body.appendChild(tr);
    });
    SEL_ESC = list.some((s) => s.id === SEL_ESC) ? SEL_ESC : (list[0]?.id || null);
    setSelectedSchoolRow(SEL_ESC);
    renderSchoolHistory(name, SEL_ESC);
    const scrollTarget = document.getElementById('munDetailCard') || document.getElementById('escCard');
    if (scrollTarget) scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (ED.track) ED.track('mun_select', { municipio: name, cre: SEL_CRE || null });
  }

  function resetDrill() {
    SEL_CRE = null;
    SEL_MUN = null;
    SEL_ESC = null;
    document.querySelectorAll('.ctile').forEach((t) => t.classList.remove('sel'));
    ['creAreaCard', 'creTrajAreasCard', 'munRow', 'munDetailCard', 'escCard'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
    hideMunDetailCard();
    hideCreTrajAreasChart();
    const kpis = document.getElementById('creAreaKpis');
    if (kpis) kpis.innerHTML = '';
    bread();
  }

  ED.initDrill = function (ctx) {
    _ctx = ctx;
    const {
      DATA, ANOS, LAST_INDEX, LAST_YEAR, PREV_INDEX, PREV_YEAR,
      MS_GERAL_2024, C, BL, CFG, NF, norm,
    } = ctx;
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
    const row = document.getElementById('creRow');
    if (row) row.innerHTML = '';
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

    function creMedSeries(o) {
      const xs = [];
      const ys = [];
      ANOS.forEach((a, i) => {
        const med = o.med?.[i];
        if (med == null || Number.isNaN(med)) return;
        xs.push(String(a));
        ys.push(med);
      });
      return { xs, ys };
    }

    function creYearAdv(o) {
      const medLast = o.med?.[LAST_INDEX];
      const medPrev = o.med?.[PREV_INDEX];
      if (medLast == null || medPrev == null || Number.isNaN(medLast) || Number.isNaN(medPrev)) return null;
      return medLast >= medPrev;
    }

    function creBelowMs(o) {
      const medLast = o.med?.[LAST_INDEX];
      const refMs = MS_GERAL_2024;
      if (medLast == null || refMs == null || Number.isNaN(medLast) || Number.isNaN(refMs)) return null;
      return medLast < refMs;
    }

    Object.keys(DATA.cre || {}).forEach((name) => {
      const o = DATA.cre[name];
      const adv = creYearAdv(o);
      const belowMs = creBelowMs(o);
      const sid = `ct_${norm(name).replace(/ /g, '_')}`;
      const t = document.createElement('div');
      t.className = `ctile${belowMs === true ? ' warn' : ''}`;
      t.onclick = () => selectCre(name);
      const arr = adv === false ? '\u25BC' : (adv === true ? '\u25B2' : '\u2014');
      const arrColor = adv === false ? C.critico : (adv === true ? C.verde : C.muted);
      t.innerHTML = `<div class="ct"><span>${ED.creDisplay(name)}</span><span class="arr" style="color:${arrColor}">${arr}</span></div><div id="${sid}" style="height:78px"></div>`;
      row.appendChild(t);
      const traj = creTrajData(o);
      const rng = creTrajRanges(o);
      const traces = [];
      let dirArrows = [];
      if (traj.xs.length >= 2) {
        dirArrows = ED.segmentDirectionArrows(traj.xs, traj.ys, {
          color: 'rgba(10,77,140,.55)',
          arrowsize: 0.55,
          arrowwidth: 1.2,
          standoff: 2,
          startstandoff: 2,
        });
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
          marker: { color: adv === false ? C.critico : (adv === true ? C.verde : C.muted), size: 8, line: { color: '#fff', width: 1 } },
          hovertemplate: '<b>%{customdata[0]}</b><br>Participa\u00e7\u00e3o: %{x:.1f}%<br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
      } else {
        const medSeries = creMedSeries(o);
        dirArrows = ED.segmentDirectionArrows(medSeries.xs, medSeries.ys, {
          color: 'rgba(10,77,140,.55)',
          arrowsize: 0.55,
          arrowwidth: 1.2,
          standoff: 2,
          startstandoff: 2,
        });
        const medPts = (o.med || []).filter((v) => v != null && !Number.isNaN(v));
        rng.y = medPts.length
          ? [Math.min(...medPts) - 4, Math.max(...medPts) + 4]
          : [460, 535];
        delete rng.x;
        traces.push({
          x: ANOS.map(String), y: o.med, mode: 'lines',
          line: { color: 'rgba(10,77,140,.55)', width: 2 },
          hovertemplate: '<b>%{x}</b><br>M\u00e9dia: %{y:.0f}<extra></extra>',
        });
        traces.push({
          x: [String(PREV_YEAR)], y: [o.med[PREV_INDEX]], mode: 'markers', marker: { color: C.borda, size: 6 },
          hovertemplate: `<b>${PREV_YEAR}</b><br>M\u00e9dia: %{y:.0f}<extra></extra>`,
        });
        traces.push({
          x: [String(ANOS[LAST_INDEX])], y: [o.med[LAST_INDEX]], mode: 'markers',
          marker: { color: adv === false ? C.critico : (adv === true ? C.verde : C.muted), size: 8, line: { color: '#fff', width: 1 } },
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
        annotations: dirArrows,
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
