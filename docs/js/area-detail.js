(function (ED) {
  let _modalBusy = false;
  let _escapeBound = false;
  let _lastDetailKey = '';

  const HIST_LABELS = [
    'Sem nota', 'Zero', '1\u2013200', '200\u2013400', '400\u2013500',
    '500\u2013600', '600\u2013800', '800\u20131000',
  ];
  const SCORE_LABELS = HIST_LABELS.slice(2);
  const HIST_COLORS = [
    '#94A3B8', '#CBD5E1', '#3BA4E8', '#0A4D8C', '#2EAD6E',
    '#F2C230', '#F07A28', '#D6453D',
  ];

  function truncName(s, n = 36) {
    return s.length > n ? `${s.slice(0, n - 1)}\u2026` : s;
  }

  function scopeData(ctx) {
    const zeroMode = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    return zeroMode === 'no_zero'
      ? {
        areaDetail: ctx.DATA.areaDetailSemZero || ctx.DATA.areaDetail || {},
        boxplot: ctx.DATA.boxplotSemZero || ctx.DATA.boxplot || {},
        histograma: ctx.DATA.histogramaSemZero || ctx.DATA.histograma || {},
        msArea: ctx.DATA.msAreaSemZero || ctx.DATA.msArea || {},
        escRank: ctx.DATA.escRankSemZero || ctx.DATA.escRank || {},
        estadualN: ctx.DATA.estadualNSemZero || ctx.DATA.estadualN || [],
        brEstadualN: ctx.DATA.brEstadualNSemZero || ctx.DATA.brEstadualN || [],
      }
      : {
        areaDetail: ctx.DATA.areaDetail || {},
        boxplot: ctx.DATA.boxplot || {},
        histograma: ctx.DATA.histograma || {},
        msArea: ctx.DATA.msArea || {},
        escRank: ctx.DATA.escRank || {},
        estadualN: ctx.DATA.estadualN || [],
        brEstadualN: ctx.DATA.brEstadualN || [],
      };
  }

  function getDetailData(ctx, areaKey, ano) {
    const scoped = scopeData(ctx);
    const ad = scoped.areaDetail?.[areaKey]?.[String(ano)];
    const i = ctx.ANOS.indexOf(Number(ano));
    if (ad) return ad;
    const bp = scoped.boxplot?.[areaKey]?.[String(ano)] || {};
    const hist = scoped.histograma?.[areaKey]?.[String(ano)]?.ms || [0, 0, 0, 0, 0, 0];
    const n = scoped.estadualN?.[i] ?? null;
    const pctZero = bp.min === 0 ? (hist[0] || 0) : 0;
    const posBins = hist.map((v, j) => (j === 0 ? Math.max(0, v - pctZero) : v));
    return {
      n,
      brN: scoped.brEstadualN?.[i] ?? null,
      pctSemNota: 0,
      pctZero,
      moda: bp.med ?? null,
      modaFaixa: null,
      modaTipo: 'faixa',
      minPos: bp.min > 0 ? bp.min : null,
      minPosExact: bp.min > 0,
      histPct: [0, pctZero, ...posBins],
      histCounts: null,
      brHistPct: null,
      brHistCounts: null,
    };
  }

  function kpiCard(label, value, color, hint) {
    const col = color ? ` style="color:${color}"` : '';
    const h = hint ? `<div class="idx-kh">${hint}</div>` : '';
    return `<div class="idx-kpi"><div class="idx-kl">${label}</div>`
      + `<div class="idx-kv"${col}>${value}</div>${h}</div>`;
  }

  function fmtN(n) {
    return n == null ? '\u2014' : Number(n).toLocaleString('pt-BR');
  }

  function pctCount(n, pct) {
    if (n == null || pct == null) return '\u2014';
    return fmtN(Math.round(n * pct / 100));
  }

  function buildAreaDetailShell(ctx, areaKey, ano) {
    const { AREANOME, ACOR, C, FMT, ANOS } = ctx;
    const scoped = scopeData(ctx);
    const nome = AREANOME[areaKey] || areaKey;
    const areaCor = ACOR[areaKey] || C.azul;
    const bp = scoped.boxplot?.[areaKey]?.[String(ano)] || {};
    const i = ANOS.indexOf(Number(ano));
    const msMed = scoped.msArea?.[areaKey]?.ms?.[i];
    const brMed = scoped.msArea?.[areaKey]?.br?.[i];
    const detail = getDetailData(ctx, areaKey, ano);
    const n = detail.n ?? scoped.estadualN?.[i] ?? null;
    const brN = detail.brN ?? scoped.brEstadualN?.[i] ?? null;
    const gap = msMed != null && brMed != null ? +(msMed - brMed).toFixed(1) : null;
    const gapCol = gap != null && gap < 0 ? C.critico : C.verde;

    const minLabel = detail.minPos != null
      ? (detail.minPosExact ? FMT(detail.minPos) : `\u2265${FMT(detail.minPos)}`)
      : '\u2014';
    const minHint = detail.minPosExact
      ? 'menor nota &gt; 0 (microdados)'
      : (detail.minPos != null ? 'limite inferior da faixa' : '');

    const modaVal = detail.moda != null ? FMT(detail.moda) : '\u2014';
    const modaHint = detail.modaTipo === 'nota'
      ? 'nota inteira mais frequente'
      : (detail.modaFaixa
        ? `faixa modal ${detail.modaFaixa} (centro ${modaVal})`
        : 'faixa com maior % de alunos');

    const kpis = [
      kpiCard('MS estadual', FMT(msMed), areaCor, 'm\u00e9dia da \u00e1rea'),
      kpiCard('Brasil estadual', FMT(brMed), C.brasil, 'refer\u00eancia nacional'),
      kpiCard('Diferen\u00e7a', gap != null ? `${gap > 0 ? '+' : ''}${FMT(gap)}` : '\u2014', gapCol),
      kpiCard('Moda', modaVal, areaCor, modaHint),
      kpiCard('M\u00edn. &gt; 0', minLabel, null, minHint),
      kpiCard('Mediana', bp.med != null ? FMT(bp.med) : '\u2014', null, 'Q2 da distribui\u00e7\u00e3o'),
      kpiCard('Zeros', detail.pctZero != null ? `${detail.pctZero.toFixed(1).replace('.', ',')}%` : '\u2014', C.muted,
        `${pctCount(n, detail.pctZero)} alunos`),
      kpiCard('Sem nota', detail.pctSemNota != null ? `${detail.pctSemNota.toFixed(1).replace('.', ',')}%` : '\u2014', C.muted,
        `${pctCount(n, detail.pctSemNota)} alunos`),
    ].join('');

    const uid = `idx_${areaKey}_${ano}`;
    return {
      nome,
      n,
      html: `<div class="idx-head">`
        + `<h4><span class="idx-dot" style="background:${areaCor}"></span>${nome} \u00b7 ${ano}</h4>`
        + `<span class="idx-sub">N = <b>${fmtN(n)}</b> participantes efetivos \u00b7 rede estadual MS \u00b7 mesma base dos histogramas</span></div>`
        + `<div class="idx-kpis">${kpis}</div>`
        + `<div class="idx-grid">`
        + `<div class="idx-panel"><h5>Distribui\u00e7\u00e3o das notas \u00b7 MS</h5><div id="${uid}_hist" class="idx-plot"></div></div>`
        + `<div class="idx-panel"><h5>MS \u00d7 Brasil \u00b7 faixas de nota</h5>`
        + `<p class="idx-cmp-note">MS: N=${fmtN(n)} participantes efetivos \u00b7 Brasil: N=${fmtN(brN)} (rede estadual nacional, mesma regra de filtro)</p>`
        + `<div id="${uid}_cmp" class="idx-plot"></div></div>`
        + `</div>`
        + `<div class="idx-ranks">`
        + `<div class="idx-panel"><h5>Top 10 escolas \u00b7 m\u00e9dia da \u00e1rea</h5><div id="${uid}_top" class="idx-plot"></div></div>`
        + `<div class="idx-panel"><h5>Bottom 10 escolas \u00b7 m\u00e9dia da \u00e1rea</h5><div id="${uid}_bot" class="idx-plot"></div></div>`
        + `</div>`,
      uid,
      detail,
      bp,
      areaCor,
      brN,
    };
  }

  function hoverHist(n, counts) {
    return (pt) => {
      const pct = pt.y;
      const i = pt.pointIndex;
      const c = counts && counts[i] != null ? counts[i] : Math.round((n || 0) * pct / 100);
      return `${pt.x}<br>${pct.toFixed(1).replace('.', ',')}% \u00b7 ${fmtN(c)} alunos<extra></extra>`;
    };
  }

  function mountAreaDetailCharts(ctx, areaKey, ano, shell) {
    const { ANOS, LAST_YEAR, C, BL, CFG } = ctx;
    const scoped = scopeData(ctx);
    const { uid, detail, areaCor, n, brN } = shell;
    const i = ANOS.indexOf(Number(ano));
    const brNVal = brN ?? detail.brN ?? scoped.brEstadualN?.[i] ?? null;
    const key = `${uid}|${areaKey}|${ano}`;
    if (_lastDetailKey === key) return;
    _lastDetailKey = key;

    const histPct = detail.histPct || [];
    const histCounts = detail.histCounts || histPct.map((p) => Math.round((n || 0) * p / 100));
    const histColors = HIST_COLORS.map((c, i) => (
      i === 0 ? '#94A3B8' : (i === 1 ? '#CBD5E1' : areaCor)
    ));

    Plotly.react(`${uid}_hist`, [{
      x: HIST_LABELS,
      y: histPct,
      type: 'bar',
      marker: { color: histColors, line: { width: 0 } },
      customdata: histCounts,
      hovertemplate: '%{x}<br>%{y:.1f}% \u00b7 %{customdata} alunos<extra></extra>',
    }], {
      ...BL,
      height: 260,
      margin: { l: 44, r: 12, t: 8, b: 72 },
      showlegend: false,
      xaxis: { tickangle: -35, tickfont: { size: 9 } },
      yaxis: {
        title: { text: '% dos alunos (N=' + fmtN(n) + ')', font: { size: 10 } },
        gridcolor: 'rgba(0,0,0,0)',
        ticksuffix: '%',
      },
    }, CFG);

    const CMP_LABELS = ['0\u2013200', '200\u2013400', '400\u2013500', '500\u2013600', '600\u2013800', '800\u20131000'];
    const msScore = histPct.slice(2);
    const msScoreC = histCounts.slice(2);
    const brPct6 = detail.brHistPct6 || scoped.histograma?.[areaKey]?.[String(ano)]?.br || [];
    const brCounts6 = detail.brHistCounts6
      || brPct6.map((p) => Math.round((brNVal || 0) * p / 100));

    Plotly.react(`${uid}_cmp`, [
      {
        x: CMP_LABELS, y: msScore, name: `MS (N=${fmtN(n)})`,
        type: 'bar', marker: { color: areaCor, opacity: 0.88 },
        customdata: msScoreC,
        hovertemplate: 'MS %{x}<br>%{y:.1f}% \u00b7 %{customdata} alunos<extra></extra>',
      },
      {
        x: CMP_LABELS, y: brPct6, name: `Brasil (N=${fmtN(brNVal)})`,
        type: 'bar', marker: { color: C.brasil, opacity: 0.88 },
        customdata: brCounts6,
        hovertemplate: 'Brasil %{x}<br>%{y:.1f}% \u00b7 %{customdata} alunos<extra></extra>',
      },
    ], {
      ...BL,
      height: 260,
      barmode: 'group',
      margin: { l: 44, r: 12, t: 8, b: 72 },
      legend: { orientation: 'h', y: -0.32, font: { size: 9 } },
      xaxis: { tickangle: -35, tickfont: { size: 8.5 } },
      yaxis: {
        title: { text: '% dos alunos (faixas positivas)', font: { size: 10 } },
        gridcolor: 'rgba(0,0,0,0)',
      },
    }, CFG);

    const escRank = (scoped.escRank && scoped.escRank[areaKey]) || [];
    const top = escRank.slice(0, 10);
    const bottom = escRank.slice(-10).reverse();

    const schoolBar = (elId, rows, cor, emptyMsg) => {
      const el = document.getElementById(elId);
      if (!el) return;
      if (!rows.length) {
        Plotly.purge(el);
        el.innerHTML = `<p class="idx-empty">${emptyMsg}</p>`;
        return;
      }
      const names = rows.map((r) => truncName(r.nome)).reverse();
      const notas = rows.map((r) => r.nota).reverse();
      const full = rows.map((r) => r.nome).reverse();
      Plotly.react(elId, [{
        y: names,
        x: notas,
        type: 'bar',
        orientation: 'h',
        marker: { color: cor, opacity: 0.88 },
        customdata: full,
        hovertemplate: '%{customdata}<br>Nota: %{x:.1f}<extra></extra>',
      }], {
        ...BL,
        height: Math.max(240, rows.length * 24 + 36),
        margin: { l: 150, r: 16, t: 6, b: 28 },
        showlegend: false,
        xaxis: { range: [0, 1000], gridcolor: 'rgba(0,0,0,0)', dtick: 200 },
        yaxis: { automargin: true, tickfont: { size: 9 } },
      }, CFG);
    };

    if (Number(ano) === LAST_YEAR) {
      schoolBar(`${uid}_top`, top, C.verde, 'Sem dados de escolas.');
      schoolBar(`${uid}_bot`, bottom, C.critico, 'Sem dados de escolas.');
    } else {
      [`${uid}_top`, `${uid}_bot`].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
          Plotly.purge(el);
          el.innerHTML = `<p class="idx-empty">Ranking de escolas dispon\u00edvel apenas para ${LAST_YEAR}.</p>`;
        }
      });
    }
  }

  function renderAreaDetail(ctx, areaKey, ano, targetId) {
    if (!areaKey) return;
    const panel = document.getElementById(targetId);
    if (!panel) return;
    panel.dataset.areaKey = areaKey;
    panel.dataset.ano = String(ano);
    const shell = buildAreaDetailShell(ctx, areaKey, ano);
    panel.innerHTML = shell.html;
    panel.classList.add('on');
    requestAnimationFrame(() => mountAreaDetailCharts(ctx, areaKey, ano, shell));
  }

  ED.showIndexDetail = function (ctx, areaKey, ano) {
    renderAreaDetail(ctx, areaKey, ano, 'indexDetail');
    document.getElementById('indexDetail')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  ED.openAreaModal = function (ctx, areaKey, ano) {
    if (!areaKey || _modalBusy) return;
    _modalBusy = true;
    const shell = buildAreaDetailShell(ctx, areaKey, ano);
    document.getElementById('areaModalTitle').textContent = `${shell.nome} \u00b7 ${ano}`;
    const body = document.getElementById('areaModalBody');
    if (body) {
      body.innerHTML = shell.html;
      requestAnimationFrame(() => mountAreaDetailCharts(ctx, areaKey, ano, shell));
    }
    document.getElementById('areaModal').classList.add('on');
    _modalBusy = false;
  };

  ED.closeAreaModal = function () {
    _modalBusy = false;
    document.getElementById('areaModal')?.classList.remove('on');
  };

  ED.initAreaDetail = function (ctx) {
    if (!_escapeBound) {
      _escapeBound = true;
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') ED.closeAreaModal();
      });
    }
    document.addEventListener('enemdash:schoolZeroMode', () => {
      const panel = document.getElementById('indexDetail');
      if (panel?.dataset?.areaKey && panel?.dataset?.ano) {
        renderAreaDetail(ctx, panel.dataset.areaKey, parseInt(panel.dataset.ano, 10), 'indexDetail');
      }
      const modal = document.getElementById('areaModal');
      if (modal?.classList.contains('on')) {
        const title = document.getElementById('areaModalTitle')?.textContent || '';
        const m = title.match(/·\s*(\d{4})$/);
        const ano = m ? parseInt(m[1], 10) : ctx.LAST_YEAR;
        const areaKey = ctx.AREAKEYS.find((k) => title.toUpperCase().includes((ctx.AREANOME[k] || '').toUpperCase()));
        if (areaKey) ED.openAreaModal(ctx, areaKey, ano);
      }
    });
    window.openAreaModal = (areaKey, ano) => ED.openAreaModal(ctx, areaKey, ano);
    window.closeAreaModal = () => ED.closeAreaModal();
    window.showIndexDetail = (areaKey, ano) => ED.showIndexDetail(ctx, areaKey, ano);
  };

  ED.initIndexDrillUi = function (ctx) {
    const sa = document.getElementById('selIndexArea');
    const sy = document.getElementById('selIndexAno');
    if (!sa || sa.dataset.init) return;
    sa.dataset.init = '1';
    ctx.AREAKEYS.forEach((k) => {
      const o = document.createElement('option');
      o.value = k;
      o.textContent = ctx.AREANOME[k];
      sa.appendChild(o);
    });
    ctx.ANOS.forEach((a) => {
      const o = document.createElement('option');
      o.value = a;
      o.textContent = a;
      sy.appendChild(o);
    });
    sy.value = ctx.ANOS[ctx.ANOS.length - 1];
    sa.value = ctx.AREAKEYS[0];
    document.getElementById('btnIndexDrill').onclick = (e) => {
      e.preventDefault();
      ED.showIndexDetail(ctx, sa.value, parseInt(sy.value, 10));
    };
  };
})(window.EnemDash);
