(function (ED) {
  ED.initStats = function (ctx) {
    const {
      DATA, ANOS, LAST_YEAR, LAST_INDEX, AREAKEYS, AREANOME, ACOR, C, CFG, MED_BR, MED_BR_SEM_ZERO,
    } = ctx;
    const {
      CFG_INTERACTIVE, layoutLineChart, hoverAreaTemplate, XSPIKE, AREANOME_FULL,
    } = ED.Config;
    const CFGI = CFG_INTERACTIVE || CFG;
    const BP = DATA.boxplot || {};
    const BP_SEM_ZERO = DATA.boxplotSemZero || {};
    const AD = DATA.areaDetail || {};
    const AD_SEM_ZERO = DATA.areaDetailSemZero || {};
    const HIST = DATA.histograma || {};
    const HIST_SEM_ZERO = DATA.histogramaSemZero || {};
    const DISP = DATA.dispersao || [];
    const DU = ED.DataUtils;

    const distArea = document.getElementById('distArea');
    const distAno = document.getElementById('distAno');
    const distAreaStrip = document.getElementById('distAreaStrip');
    const distFocusCaption = document.getElementById('distFocusCaption');
    const distBoxStats = document.getElementById('distBoxStats');
    const distSnapTitle = document.getElementById('distSnapTitle');
    const distSnapKpis = document.getElementById('distSnapKpis');
    const histCaption = document.getElementById('histCaption');

    function currentZeroMode() {
      return ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    }

    function selectedArea() {
      return distArea?.value || 'CN';
    }

    function selectedAno() {
      return String(distAno?.value || LAST_YEAR);
    }

    function setArea(k, opts = {}) {
      if (!AREAKEYS.includes(k)) return;
      if (distArea) distArea.value = k;
      syncAreaStrip();
      if (opts.render !== false) refreshDist();
    }

    function setAno(a, opts = {}) {
      const s = String(a);
      if (distAno && [...distAno.options].some((o) => o.value === s)) {
        distAno.value = s;
      }
      if (opts.render !== false) {
        renderFocusBoxplot();
        refreshSnapshot();
      }
    }

    function boxMinPos(d, areaKey, ano, detailData) {
      const mp = d.min_pos ?? d.minPos ?? detailData?.[areaKey]?.[String(ano)]?.minPos;
      if (mp != null && mp > 0) return mp;
      if (d.min != null && d.min > 0) return d.min;
      return null;
    }

    const BOX_X_FLOOR = 250;

    function boxXRange(lowerVals, q1Vals, q3Vals, maxVals, brVals) {
      const nums = [...lowerVals, ...q1Vals, ...q3Vals, ...maxVals, ...(brVals || [])]
        .filter((v) => v != null && !Number.isNaN(v));
      if (!nums.length) return [BOX_X_FLOOR, 1000];
      const lo = Math.max(BOX_X_FLOOR, Math.floor((Math.min(...nums) - 25) / 25) * 25);
      const hi = Math.min(1000, Math.ceil((Math.max(...nums) + 25) / 25) * 25);
      return [lo, Math.max(hi, lo + 100)];
    }

    function boxXTicks(xLo, xHi) {
      const marks = [];
      for (let v = Math.ceil(xLo / 50) * 50; v <= xHi; v += 50) marks.push(v);
      return marks.length ? marks : [xLo, xHi];
    }

    function buildBoxSeries(k, boxData, detailData) {
      const xVals = [];
      const q1Vals = [];
      const medVals = [];
      const q3Vals = [];
      const nVals = [];
      const lowerVals = [];
      const maxVals = [];
      const minMarkerX = [];
      const minMarkerY = [];
      ANOS.slice().reverse().forEach((a) => {
        const d = (boxData[k] || {})[String(a)];
        if (!d) return;
        const mp = boxMinPos(d, k, a, detailData);
        const detail = detailData?.[k]?.[String(a)] || {};
        xVals.push(String(a));
        q1Vals.push(d.q1);
        medVals.push(d.med);
        q3Vals.push(d.q3);
        nVals.push(detail.n ?? null);
        lowerVals.push(mp != null ? mp : (d.min > 0 ? d.min : d.q1));
        maxVals.push(d.max);
        if (mp != null) {
          minMarkerX.push(mp);
          minMarkerY.push(String(a));
        }
      });
      return {
        xVals, q1Vals, medVals, q3Vals, nVals, lowerVals, maxVals, minMarkerX, minMarkerY,
      };
    }

    function brSeriesForArea(k, zeroMode) {
      const src = zeroMode === 'no_zero'
        ? (DATA.msAreaSemZero || DATA.msArea || {})
        : (DATA.msArea || {});
      return src[k]?.br || [];
    }

    function brMeanAtYear(k, ano, zeroMode) {
      const series = brSeriesForArea(k, zeroMode);
      const idx = ANOS.indexOf(Number(ano));
      if (idx < 0) return null;
      const v = series[idx];
      return v != null && !Number.isNaN(v) ? v : null;
    }

    function fmt1(v) {
      return v == null || Number.isNaN(v) ? '\u2014' : v.toFixed(1).replace('.', ',');
    }

    function fmt0(v) {
      return v == null || Number.isNaN(v) ? '\u2014' : String(Math.round(v));
    }

    function fmtDelta(v) {
      if (v == null || Number.isNaN(v)) return '\u2014';
      const n = Math.round(v);
      return `${n >= 0 ? '+' : ''}${n}`;
    }

    function syncAreaStrip() {
      if (!distAreaStrip) return;
      const active = selectedArea();
      distAreaStrip.querySelectorAll('.dist-area-chip').forEach((btn) => {
        const on = btn.dataset.area === active;
        btn.classList.toggle('is-active', on);
        btn.setAttribute('aria-selected', on ? 'true' : 'false');
      });
    }

    function buildAreaStrip() {
      if (!distAreaStrip) return;
      const zeroMode = currentZeroMode();
      const boxData = zeroMode === 'no_zero' ? BP_SEM_ZERO : BP;
      distAreaStrip.innerHTML = AREAKEYS.map((k) => {
        const d = (boxData[k] || {})[String(LAST_YEAR)] || {};
        const med = d.med;
        const q1 = d.q1;
        const q3 = d.q3;
        const iqr = (q1 != null && q3 != null) ? q3 - q1 : null;
        const nome = (AREANOME_FULL && AREANOME_FULL[k]) || AREANOME[k];
        return `<button type="button" class="dist-area-chip" role="tab" data-area="${k}" aria-selected="false" style="--chip:${ACOR[k]}" title="Mediana ${fmt0(med)}${iqr != null ? ` · IQR (Q3−Q1) = ${fmt0(iqr)}` : ''} em ${LAST_YEAR}">
          <span class="dist-area-chip-dot" aria-hidden="true"></span>
          <span class="dist-area-chip-body">
            <span class="dist-area-chip-name">${nome}</span>
            <span class="dist-area-chip-meta">mediana ${fmt0(med)}${iqr != null ? ` · IQR ${fmt0(iqr)}` : ''} · ${LAST_YEAR}</span>
          </span>
        </button>`;
      }).join('');
      distAreaStrip.querySelectorAll('.dist-area-chip').forEach((btn) => {
        btn.onclick = () => setArea(btn.dataset.area);
      });
      syncAreaStrip();
    }

    const boxLayoutBase = {
      showlegend: false,
      margin: { l: 52, r: 36, t: 10, b: 36 },
    };

    function renderFocusBoxplot() {
      const k = selectedArea();
      const zeroMode = currentZeroMode();
      const boxData = zeroMode === 'no_zero' ? BP_SEM_ZERO : BP;
      const detailData = zeroMode === 'no_zero' ? AD_SEM_ZERO : AD;
      const s = buildBoxSeries(k, boxData, detailData);
      const el = document.getElementById('g_box_focus');
      if (!el || !s.xVals.length) return;

      const brAtYear = s.xVals.map((ano) => brMeanAtYear(k, ano, zeroMode));
      const [xLo, xHi] = boxXRange(s.lowerVals, s.q1Vals, s.q3Vals, s.maxVals, brAtYear);
      const xTicks = boxXTicks(xLo, xHi);
      const cor = ACOR[k];
      const nome = (AREANOME_FULL && AREANOME_FULL[k]) || AREANOME[k];
      const rowH = 28;
      const h = Math.max(360, Math.min(440, s.xVals.length * rowH + 56));
      el.style.minHeight = `${h}px`;

      if (distFocusCaption) {
        distFocusCaption.textContent = `${nome} · MS estadual · ${ANOS[0]}\u2013${LAST_YEAR}`
          + `${zeroMode === 'no_zero' ? ' · excluindo notas zero' : ''}`
          + ' · pontos cinza = m\u00e9dia BR (esc. estaduais)';
      }

      const gridShapes = xTicks.map((xv) => ({
        type: 'line',
        x0: xv, x1: xv, y0: 0, y1: 1,
        xref: 'x', yref: 'paper',
        line: { color: 'rgba(0,0,0,0.05)', width: 1 },
        layer: 'below',
      }));

      const selAno = selectedAno();
      const selIdx = s.xVals.indexOf(selAno);
      if (selIdx >= 0) {
        gridShapes.push({
          type: 'rect',
          x0: xLo,
          x1: xHi,
          y0: selIdx - 0.42,
          y1: selIdx + 0.42,
          xref: 'x',
          yref: 'y',
          fillcolor: `rgba(${DU.hexToRgb(cor)},0.10)`,
          line: { width: 0 },
          layer: 'below',
        });
      }

      if (distBoxStats) {
        if (selIdx >= 0) {
          const med = s.medVals[selIdx];
          const q1 = s.q1Vals[selIdx];
          const q3 = s.q3Vals[selIdx];
          const lo = s.lowerVals[selIdx];
          const hi = s.maxVals[selIdx];
          const br = brAtYear[selIdx];
          const n = s.nVals[selIdx];
          distBoxStats.innerHTML = `
            <span class="dist-box-stats-year" style="--chip:${cor}">${selAno}</span>
            <span class="dist-box-stat"><b>N</b> ${n ?? '\u2014'}</span>
            <span class="dist-box-stat"><b>m\u00edn&gt;0</b> ${fmt0(lo)}</span>
            <span class="dist-box-stat"><b>Q1</b> ${fmt0(q1)}</span>
            <span class="dist-box-stat dist-box-stat-med"><b>mediana</b> ${fmt0(med)}</span>
            <span class="dist-box-stat"><b>Q3</b> ${fmt0(q3)}</span>
            <span class="dist-box-stat"><b>m\u00e1x</b> ${fmt0(hi)}</span>
            <span class="dist-box-stat dist-box-stat-br"><b>m\u00e9dia BR</b> ${fmt0(br)}</span>`;
        } else {
          distBoxStats.innerHTML = '';
        }
      }

      const annotations = [];
      if (selIdx >= 0 && s.medVals[selIdx] != null) {
        annotations.push({
          x: s.medVals[selIdx],
          y: s.xVals[selIdx],
          text: fmt0(s.medVals[selIdx]),
          showarrow: false,
          textangle: 0,
          xanchor: 'center',
          yanchor: 'middle',
          font: { size: 11, color: '#fff', family: 'Segoe UI, system-ui, sans-serif' },
          bgcolor: cor,
          borderpad: 3,
          bordercolor: cor,
          borderwidth: 0,
          opacity: 0.96,
        });
      }

      const hoverLabelClean = {
        bgcolor: 'rgba(255,255,255,0.94)',
        bordercolor: 'rgba(255,255,255,0)',
        font: { size: 12, color: C.txt, family: 'Segoe UI, system-ui, sans-serif' },
        align: 'left',
        namelength: -1,
      };

      function noteHoverTrace(xs, ys, name) {
        const x = [];
        const y = [];
        xs.forEach((v, i) => {
          if (v == null || Number.isNaN(v) || ys[i] == null) return;
          x.push(v);
          y.push(ys[i]);
        });
        if (!x.length) return null;
        return {
          x,
          y,
          mode: 'markers',
          type: 'scatter',
          name,
          marker: { size: 14, opacity: 0 },
          hovertemplate: '%{x:.0f}<extra></extra>',
          hoverlabel: hoverLabelClean,
          showlegend: false,
        };
      }

      const traces = [{
        y: s.xVals,
        q1: s.q1Vals,
        median: s.medVals,
        q3: s.q3Vals,
        lowerfence: s.lowerVals,
        upperfence: s.maxVals,
        type: 'box',
        orientation: 'h',
        name: 'MS',
        boxpoints: false,
        hoverinfo: 'skip',
        whiskerwidth: 0.65,
        width: 0.62,
        marker: { color: cor },
        line: { color: cor, width: 2.2 },
        fillcolor: `rgba(${DU.hexToRgb(cor)},0.28)`,
      }];

      [
        noteHoverTrace(s.q1Vals, s.xVals, 'Q1'),
        noteHoverTrace(s.medVals, s.xVals, 'Q2'),
        noteHoverTrace(s.q3Vals, s.xVals, 'Q3'),
        noteHoverTrace(s.maxVals, s.xVals, 'm\u00e1x'),
      ].forEach((t) => { if (t) traces.push(t); });

      if (s.minMarkerX.length) {
        traces.push({
          x: s.minMarkerX,
          y: s.minMarkerY,
          mode: 'markers',
          type: 'scatter',
          name: 'm\u00edn > 0',
          marker: {
            symbol: 'diamond',
            size: 8,
            color: '#fff',
            line: { color: cor, width: 2.2 },
          },
          hovertemplate: '%{x:.0f}<extra></extra>',
          hoverlabel: hoverLabelClean,
          showlegend: false,
        });
      }

      const brX = [];
      const brY = [];
      s.xVals.forEach((ano, idx) => {
        const v = brAtYear[idx];
        if (v != null) {
          brX.push(v);
          brY.push(ano);
        }
      });
      if (brX.length) {
        traces.push({
          x: brX,
          y: brY,
          mode: 'markers+lines',
          type: 'scatter',
          name: 'M\u00e9dia BR (esc. estaduais)',
          line: { color: C.brasil, width: 1.2, dash: 'dot' },
          marker: {
            symbol: 'circle-open',
            size: 9,
            color: C.brasil,
            line: { color: C.brasil, width: 2 },
          },
          hovertemplate: '%{x:.0f}<extra></extra>',
          hoverlabel: hoverLabelClean,
        });
      }

      Plotly.react('g_box_focus', traces, ED.withPandemia({
        ...boxLayoutBase,
        height: h,
        hovermode: 'closest',
        hoverdistance: 30,
        shapes: gridShapes,
        annotations,
        hoverlabel: {
          bgcolor: 'rgba(255,255,255,0.94)',
          bordercolor: 'rgba(255,255,255,0)',
          font: { size: 12, color: C.txt, family: 'Segoe UI, system-ui, sans-serif' },
          align: 'left',
          namelength: -1,
        },
        xaxis: {
          title: { text: 'nota', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          range: [xLo, xHi],
          tickvals: xTicks.length ? xTicks : undefined,
          dtick: xTicks.length ? undefined : 50,
          tickfont: { size: 10 },
          tickangle: 0,
          automargin: true,
        },
        yaxis: {
          gridcolor: 'rgba(0,0,0,0)',
          tickfont: { size: 11, color: C.muted },
          tickangle: 0,
          automargin: true,
          type: 'category',
          categoryorder: 'array',
          categoryarray: s.xVals,
          autorange: false,
          range: [s.xVals.length - 0.5, -0.5],
          ...XSPIKE,
        },
      }, {
        x0: xLo,
        x1: xHi,
        y0: '2019',
        y1: '2021',
        xref: 'x',
        yref: 'y',
        annotate: false,
      }), CFG);

      if (!el.dataset.distClickBound) {
        el.dataset.distClickBound = '1';
        el.on('plotly_click', (ev) => {
          const pt = ev?.points?.[0];
          if (!pt) return;
          const ano = pt.y != null ? String(pt.y) : null;
          if (ano && /^\d{4}$/.test(ano)) setAno(ano);
        });
      }
    }

    function highBandPct(bins) {
      if (!bins || bins.length < 6) return null;
      const a = bins[4];
      const b = bins[5];
      if (a == null && b == null) return null;
      return (a || 0) + (b || 0);
    }

    function renderSnapKpis() {
      if (!distSnapKpis) return;
      const k = selectedArea();
      const a = selectedAno();
      const zeroMode = currentZeroMode();
      const boxData = zeroMode === 'no_zero' ? BP_SEM_ZERO : BP;
      const histData = zeroMode === 'no_zero' ? HIST_SEM_ZERO : HIST;
      const bp = (boxData[k] || {})[a] || {};
      const hist = (histData[k] || {})[a] || {};
      const medMs = bp.med ?? null;
      const brMed = brMeanAtYear(k, a, zeroMode);
      const gap = medMs != null && brMed != null ? medMs - brMed : null;
      const highMs = highBandPct(hist.ms);
      const highBr = highBandPct(hist.br);
      const gapCls = gap == null ? '' : (gap >= 0 ? 'above' : 'below');

      distSnapKpis.innerHTML = `
        <div class="dist-snap-kpi">
          <p class="dist-snap-lbl">Mediana MS</p>
          <div class="dist-snap-val" style="color:${ACOR[k]}">${fmt1(medMs)}</div>
          <p class="dist-snap-sub">${AREANOME[k]} · ${a}</p>
        </div>
        <div class="dist-snap-kpi">
          <p class="dist-snap-lbl">M\u00e9dia BR</p>
          <div class="dist-snap-val" style="color:${C.brasil}">${fmt1(brMed)}</div>
          <p class="dist-snap-sub">esc. estaduais</p>
        </div>
        <div class="dist-snap-kpi">
          <p class="dist-snap-lbl">Gap MS \u2212 BR</p>
          <div class="dist-snap-val ${gapCls}">${fmtDelta(gap)}</div>
          <p class="dist-snap-sub">pontos (mediana vs m\u00e9dia)</p>
        </div>
        <div class="dist-snap-kpi">
          <p class="dist-snap-lbl">% notas \u2265 600</p>
          <div class="dist-snap-val">${highMs != null ? `${fmt1(highMs)}%` : '\u2014'}</div>
          <p class="dist-snap-sub">MS · BR ${highBr != null ? `${fmt1(highBr)}%` : '\u2014'}</p>
        </div>`;
    }

    function renderHist() {
      const k = selectedArea();
      const a = selectedAno();
      const zeroMode = currentZeroMode();
      const histData = zeroMode === 'no_zero' ? HIST_SEM_ZERO : HIST;
      const d = (histData[k] || {})[a];
      const nome = (AREANOME_FULL && AREANOME_FULL[k]) || AREANOME[k];
      if (distSnapTitle) {
        const span = distSnapTitle.querySelector('span');
        if (span) span.textContent = `${nome} · ${a}`;
      }
      if (!d) {
        if (histCaption) histCaption.textContent = `${nome} · ${a} · sem dados de faixas neste recorte`;
        return;
      }
      const cor = ACOR[k];
      const faixas = ['0\u2013200', '200\u2013400', '400\u2013500', '500\u2013600', '600\u2013800', '800\u20131000'];
      if (histCaption) {
        histCaption.textContent = `${nome} · ${a} · participantes efetivos (esc. estaduais)`
          + `${zeroMode === 'no_zero' ? ' · excluindo notas zero' : ''}`;
      }
      document.querySelectorAll('.hist-dot-ms').forEach((el) => { el.style.background = cor; });
      Plotly.react('g_histograma', [
        {
          x: faixas,
          y: d.ms,
          name: 'MS estadual',
          type: 'bar',
          marker: { color: cor, line: { width: 0 }, opacity: 0.92 },
          hovertemplate: hoverAreaTemplate('MS estadual').replace('%{y:.0f}', '%{y:.1f}%'),
        },
        {
          x: faixas,
          y: d.br,
          name: 'Brasil (esc. estaduais)',
          type: 'bar',
          marker: { color: 'rgba(123,135,148,0.28)', line: { color: C.brasil, width: 1.5 }, opacity: 1 },
          hovertemplate: hoverAreaTemplate('Brasil (esc. estaduais)').replace('%{y:.0f}', '%{y:.1f}%'),
        },
      ], layoutLineChart({
        height: 340,
        barmode: 'group',
        bargap: 0.24,
        bargroupgap: 0.06,
        showlegend: false,
        margin: { l: 48, r: 16, t: 10, b: 48 },
        xaxis: {
          title: { text: 'faixa de nota', font: { size: 10 } },
          tickfont: { size: 10 },
          tickangle: -18,
          gridcolor: 'rgba(0,0,0,0)',
          showgrid: false,
          ...XSPIKE,
        },
        yaxis: {
          title: { text: '% dos alunos', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          showgrid: false,
          ticksuffix: '%',
          rangemode: 'tozero',
        },
      }), CFG);
    }

    function refreshSnapshot() {
      renderSnapKpis();
      renderHist();
    }

    function refreshDist() {
      buildAreaStrip();
      renderFocusBoxplot();
      refreshSnapshot();
    }

    if (distArea) {
      AREAKEYS.forEach((k) => {
        const o = document.createElement('option');
        o.value = k;
        o.textContent = (AREANOME_FULL && AREANOME_FULL[k]) || AREANOME[k];
        distArea.appendChild(o);
      });
      distArea.value = 'CN';
      distArea.onchange = () => {
        syncAreaStrip();
        refreshDist();
      };
    }
    if (distAno) {
      ANOS.forEach((a) => {
        const o = document.createElement('option');
        o.value = a;
        o.textContent = a;
        distAno.appendChild(o);
      });
      distAno.value = String(LAST_YEAR);
      distAno.onchange = () => {
        renderFocusBoxplot();
        refreshSnapshot();
      };
    }

    /* Cores fixas por CRE — pares que se confundiam ficam em matizes opostos. */
    const CRE_COLOR_BY_KEY = {
      sed: '#1A237E',           /* índigo */
      'cg metrop': '#C62828',   /* vermelho */
      'cg metrop.': '#C62828',
      'tres lagoas': '#00838F', /* teal — longe do vermelho da CG */
      'três lagoas': '#00838F',
      corumba: '#2E7D32',       /* verde */
      corumbá: '#2E7D32',
      coxim: '#EF6C00',         /* laranja — longe do verde de Corumbá */
      'ponta pora': '#AD1457',  /* magenta — longe do índigo principal */
      'ponta porã': '#AD1457',
      aquidauana: '#1565C0',    /* azul */
      dourados: '#6A1B9A',      /* roxo */
      jardim: '#4E342E',        /* marrom */
      navirai: '#558B2F',       /* oliva */
      naviraí: '#558B2F',
      'nova andradina': '#F57F17', /* âmbar */
      paranaiba: '#283593',     /* índigo claro */
      paranaíba: '#283593',
    };
    const crePaletteFallback = [
      '#0A3D62', '#C62828', '#1B7A4E', '#6A1B9A', '#E65100', '#00695C',
      '#AD1457', '#1565C0', '#558B2F', '#4E342E', '#283593', '#B71C1C',
    ];
    const creList = [...new Set(DISP.map((e) => e.cre).filter(Boolean))].sort((a, b) => {
      const aSed = /SED/i.test(a);
      const bSed = /SED/i.test(b);
      if (aSed && !bSed) return -1;
      if (bSed && !aSed) return 1;
      return a.localeCompare(b, 'pt-BR');
    });
    function creColorKey(name) {
      return ED.DataUtils.norm(ED.creDisplay(name)).toLowerCase();
    }
    const creColors = {};
    let fallbackIdx = 0;
    creList.forEach((c) => {
      const key = creColorKey(c);
      const mapped = CRE_COLOR_BY_KEY[key]
        || CRE_COLOR_BY_KEY[key.replace(/\./g, '')]
        || null;
      if (mapped) {
        creColors[c] = mapped;
      } else {
        creColors[c] = crePaletteFallback[fallbackIdx % crePaletteFallback.length];
        fallbackIdx += 1;
      }
    });

    const dispCre = document.getElementById('dispCre');
    const dispCaption = document.getElementById('dispCaption');
    const dispLegend = document.getElementById('dispLegend');
    const creHidden = new Set();
    document.querySelectorAll('[data-school-zero-mode]').forEach((el) => {
      if (el.dataset.zeroModeBound === '1') return;
      el.dataset.zeroModeBound = '1';
      el.onchange = () => {
        if (ED.setSchoolZeroMode) ED.setSchoolZeroMode(el.value);
      };
    });
    if (dispCre) {
      const allOpt = document.createElement('option');
      allOpt.value = '';
      allOpt.textContent = 'Todas as CREs';
      dispCre.appendChild(allOpt);
      creList.forEach((cre) => {
        const o = document.createElement('option');
        o.value = cre;
        o.textContent = ED.creDisplay(cre);
        dispCre.appendChild(o);
      });
    }

    function dispXMax(vals) {
      const v = vals.filter((x) => x != null && !Number.isNaN(x)).sort((a, b) => a - b);
      if (!v.length) return 120;
      const p98 = v[Math.min(v.length - 1, Math.floor(v.length * 0.98))];
      return Math.min(180, Math.max(115, Math.ceil((p98 + 5) / 5) * 5));
    }

    function bubbleSize(n) {
      return Math.max(8, Math.min(28, Math.sqrt(n) * 1.45));
    }

    function buildDispLegend(onToggle) {
      if (!dispLegend) return;
      dispLegend.innerHTML = creList.map((cre) => {
        const off = creHidden.has(cre) ? ' off' : '';
        return `<button type="button" class="disp-chip${off}" data-cre="${cre}" style="--chip:${creColors[cre]}">`
          + `<span class="disp-chip-dot"></span>${ED.creDisplay(cre)}</button>`;
      }).join('');
      dispLegend.querySelectorAll('.disp-chip').forEach((btn) => {
        btn.onclick = () => onToggle(btn.dataset.cre);
      });
    }

    function renderDisp() {
      const creFilter = dispCre?.value || '';
      const zeroMode = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
      const msMed = zeroMode === 'no_zero' && ctx.MS_GERAL_2024_SEM_ZERO != null
        ? ctx.MS_GERAL_2024_SEM_ZERO
        : ctx.DATA.medMs?.[ANOS.length - 1];
      const brMed = zeroMode === 'no_zero'
        ? (MED_BR_SEM_ZERO?.[LAST_INDEX] ?? MED_BR?.[LAST_INDEX])
        : MED_BR?.[LAST_INDEX];
      const pts = DISP.map((e) => {
        if (zeroMode !== 'no_zero') return e;
        return {
          ...e,
          nota: e.notaSemZero ?? null,
          n: e.nSemZero ?? 0,
          tx: e.txSemZero ?? null,
        };
      }).filter((e) => {
        if (creFilter && e.cre !== creFilter) return false;
        if (creHidden.has(e.cre)) return false;
        if (e.nota == null || !e.n) return false;
        return true;
      });
      const txs = pts.map((e) => e.tx ?? 0);
      const xMax = dispXMax(txs);
      const yVals = pts.map((e) => e.nota).filter((v) => v != null);
      const yMin = yVals.length ? Math.floor(Math.min(...yVals) / 25) * 25 - 25 : 350;
      const yMax = yVals.length ? Math.ceil(Math.max(...yVals) / 25) * 25 + 25 : 600;

      const traces = creList
        .filter((cre) => !creHidden.has(cre) && (!creFilter || cre === creFilter))
        .map((cre) => {
          const sub = pts.filter((e) => e.cre === cre);
          return {
            x: sub.map((e) => e.tx ?? 0),
            y: sub.map((e) => e.nota),
            text: sub.map((e) => e.nome),
            customdata: sub.map((e) => [
              e.nome || '\u2014',
              e.mun || '\u2014',
              ED.creDisplay(e.cre || cre),
              e.concl != null ? e.concl : '\u2014',
              e.tx != null ? `${Number(e.tx).toFixed(1).replace('.', ',')}%` : '\u2014',
            ]),
            mode: 'markers',
            type: 'scatter',
            name: cre,
            marker: {
              size: sub.map((e) => bubbleSize(e.n || 1)),
              color: creColors[cre],
              opacity: 0.78,
              line: { color: '#fff', width: 1.4 },
            },
            hovertemplate:
              '<b>%{customdata[0]}</b><br>'
              + 'Munic\u00edpio: %{customdata[1]}<br>'
              + 'CRE: %{customdata[2]}<br>'
              + 'Concluintes: %{customdata[3]}<br>'
              + 'Participa\u00e7\u00e3o: %{customdata[4]}<br>'
              + 'M\u00e9dia geral: %{y:.1f}<extra></extra>',
            hoverlabel: {
              bgcolor: '#fff',
              bordercolor: creColors[cre],
              font: {
                size: 12,
                color: creColors[cre],
                family: 'Segoe UI, system-ui, sans-serif',
              },
            },
          };
        });

      const shapes = [{
        type: 'line',
        x0: 100, x1: 100, y0: yMin, y1: yMax,
        line: { color: 'rgba(240,122,40,.55)', width: 1.5, dash: 'dot' },
      }];
      const annotations = [{
        x: 100, y: yMax, xanchor: 'center', yanchor: 'bottom',
        text: '100%', showarrow: false,
        font: { size: 9, color: '#B45309' },
      }];
      if (msMed != null) {
        shapes.push({
          type: 'line',
          x0: 0, x1: xMax, y0: msMed, y1: msMed,
          line: { color: 'rgba(123,135,148,.65)', width: 1.5, dash: 'dot' },
        });
        annotations.push({
          x: xMax, y: msMed, xanchor: 'right', yanchor: 'bottom',
          text: `MS ${msMed.toFixed(0)}`, showarrow: false,
          font: { size: 9, color: C.brasil },
        });
      }
      if (brMed != null) {
        shapes.push({
          type: 'line',
          x0: 0, x1: xMax, y0: brMed, y1: brMed,
          line: { color: 'rgba(138,155,176,.85)', width: 1.4, dash: 'dash' },
        });
        annotations.push({
          x: 0, y: brMed, xanchor: 'left', yanchor: 'bottom',
          text: `BR ${brMed.toFixed(0)}`, showarrow: false,
          font: { size: 9, color: C.brasil },
        });
      }

      Plotly.react('g_dispersao', traces, layoutLineChart({
        height: 360,
        hovermode: 'closest',
        showlegend: false,
        margin: { l: 50, r: 16, t: 28, b: 48 },
        xaxis: {
          title: { text: 'participa\u00e7\u00e3o efetiva (%)', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          showgrid: false,
          zeroline: false,
          range: [0, xMax],
          ticksuffix: '%',
          dtick: xMax > 130 ? 25 : 20,
          ...XSPIKE,
        },
        yaxis: {
          title: { text: 'm\u00e9dia geral', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          showgrid: false,
          zeroline: false,
          range: [Math.max(300, yMin), Math.min(650, yMax)],
        },
        shapes,
        annotations,
      }), CFGI);

      if (dispCaption) {
        const nOver = pts.filter((e) => (e.tx ?? 0) > 100).length;
        const creLbl = creFilter ? ED.creDisplay(creFilter) : 'todas as CREs';
        const zeroLbl = zeroMode === 'no_zero' ? 'excluindo notas zero' : 'incluindo notas zero';
        dispCaption.textContent = `${pts.length} escolas · ${creLbl} · ${zeroLbl} · eixo X at\u00e9 ${xMax}%`
          + (nOver ? ` \u00b7 ${nOver} com participa\u00e7\u00e3o > 100%` : '');
      }
    }

    function toggleCreChip(cre) {
      if (creHidden.has(cre)) creHidden.delete(cre);
      else creHidden.add(cre);
      buildDispLegend(toggleCreChip);
      renderDisp();
    }

    buildDispLegend(toggleCreChip);
    if (dispCre) dispCre.onchange = renderDisp;
    document.addEventListener('enemdash:schoolZeroMode', () => {
      refreshDist();
      renderDisp();
    });

    refreshDist();
    renderDisp();
  };
})(window.EnemDash);
