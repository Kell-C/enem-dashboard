(function (ED) {
  ED.initStats = function (ctx) {
    const { DATA, ANOS, LAST_YEAR, AREAKEYS, AREANOME, ACOR, C, BL, CFG } = ctx;
    const CFGI = ED.Config.CFG_INTERACTIVE || CFG;
    const BP = DATA.boxplot || {};
    const BP_SEM_ZERO = DATA.boxplotSemZero || {};
    const AD = DATA.areaDetail || {};
    const AD_SEM_ZERO = DATA.areaDetailSemZero || {};
    const HIST = DATA.histograma || {};
    const HIST_SEM_ZERO = DATA.histogramaSemZero || {};
    const DISP = DATA.dispersao || [];
    const DU = ED.DataUtils;

    function currentZeroMode() {
      return ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    }

    function boxMinPos(d, areaKey, ano, detailData) {
      const mp = d.min_pos ?? d.minPos ?? detailData?.[areaKey]?.[String(ano)]?.minPos;
      if (mp != null && mp > 0) return mp;
      if (d.min != null && d.min > 0) return d.min;
      return null;
    }

    const boxLayoutBase = {
      ...BL,
      showlegend: false,
      hoverlabel: { bgcolor: '#fff', bordercolor: C.borda, font: { size: 11, color: C.muted } },
      margin: { l: 38, r: 10, t: 2, b: 26 },
    };

    function renderBoxplots() {
      const zeroMode = currentZeroMode();
      const boxData = zeroMode === 'no_zero' ? BP_SEM_ZERO : BP;
      const detailData = zeroMode === 'no_zero' ? AD_SEM_ZERO : AD;
      AREAKEYS.forEach((k) => {
        const cor = ACOR[k];
        const xVals = [];
        const q1Vals = [];
        const medVals = [];
        const q3Vals = [];
        const minPosVals = [];
        const lowerVals = [];
        const maxVals = [];
        const minMarkerX = [];
        const minMarkerY = [];
        ANOS.forEach((a) => {
          const d = (boxData[k] || {})[String(a)];
          if (!d) return;
          const mp = boxMinPos(d, k, a, detailData);
          xVals.push(String(a));
          q1Vals.push(d.q1);
          medVals.push(d.med);
          q3Vals.push(d.q3);
          minPosVals.push(mp);
          lowerVals.push(mp != null ? mp : (d.min > 0 ? d.min : d.q1));
          maxVals.push(d.max);
          if (mp != null) {
            minMarkerX.push(mp);
            minMarkerY.push(String(a));
          }
        });
        if (xVals.length === 0) return;
        const h = Math.max(118, xVals.length * 22 + 36);
        const traces = [{
          y: xVals,
          q1: q1Vals,
          median: medVals,
          q3: q3Vals,
          lowerfence: lowerVals,
          upperfence: maxVals,
          customdata: minPosVals.map((v) => (v != null ? v.toFixed(1) : '\u2014')),
          type: 'box',
          orientation: 'h',
          boxpoints: false,
          marker: { color: cor },
          line: { color: cor, width: 2 },
          fillcolor: `rgba(${DU.hexToRgb(cor)},0.18)`,
          hovertemplate: `${AREANOME[k]} · %{y}<br>Mediana: %{median:.1f}<br>Q1–Q3: %{q1:.1f} – %{q3:.1f}<br>M\u00edn. &gt; 0: %{customdata}<br>M\u00e1x: %{upperfence:.1f}<extra></extra>`,
        }];
        if (minMarkerX.length) {
          traces.push({
            x: minMarkerX,
            y: minMarkerY,
            mode: 'markers',
            type: 'scatter',
            marker: {
              symbol: 'diamond',
              size: 7,
              color: '#fff',
              line: { color: cor, width: 2 },
            },
            hovertemplate: `M\u00edn. &gt; 0: %{x:.1f}<extra></extra>`,
            showlegend: false,
          });
        }
        Plotly.react(`g_box_${k}`, traces, {
          ...boxLayoutBase,
          height: h,
          xaxis: {
            title: { text: 'nota', font: { size: 10 } },
            gridcolor: 'rgba(0,0,0,0)',
            range: [0, 1000],
            dtick: 250,
            tickfont: { size: 10 },
          },
          yaxis: {
            gridcolor: 'rgba(0,0,0,0)',
            dtick: 1,
            tickfont: { size: 10, color: C.muted },
          },
        }, CFG);
      });
    }
    renderBoxplots();

    const hArea = document.getElementById('histArea');
    const hAno = document.getElementById('histAno');
    const histCaption = document.getElementById('histCaption');
    AREAKEYS.forEach((k) => {
      const o = document.createElement('option');
      o.value = k;
      o.textContent = AREANOME[k];
      hArea.appendChild(o);
    });
    ANOS.forEach((a) => {
      const o = document.createElement('option');
      o.value = a;
      o.textContent = a;
      hAno.appendChild(o);
    });
    hArea.value = 'CN';
    hAno.value = String(LAST_YEAR);

    function renderHist() {
      const k = hArea.value;
      const a = String(hAno.value);
      const zeroMode = currentZeroMode();
      const histData = zeroMode === 'no_zero' ? HIST_SEM_ZERO : HIST;
      const d = (histData[k] || {})[a];
      if (!d) return;
      const cor = ACOR[k];
      const faixas = ['0\u2013200', '200\u2013400', '400\u2013500', '500\u2013600', '600\u2013800', '800\u20131000'];
      if (histCaption) {
        histCaption.textContent = `${AREANOME[k]} · ${a} · participantes efetivos${zeroMode === 'no_zero' ? ' · excluindo notas zero' : ''}`;
      }
      document.querySelectorAll('.hist-dot-ms').forEach((el) => { el.style.background = cor; });
      Plotly.react('g_histograma', [
        {
          x: faixas,
          y: d.ms,
          name: 'MS estadual',
          type: 'bar',
          marker: { color: cor, line: { width: 0 }, opacity: 0.92 },
          hovertemplate: 'MS · %{x}<br>%{y:.1f}% dos alunos<extra></extra>',
        },
        {
          x: faixas,
          y: d.br,
          name: 'Brasil estadual',
          type: 'bar',
          marker: { color: 'rgba(123,135,148,0.28)', line: { color: C.brasil, width: 1.5 }, opacity: 1 },
          hovertemplate: 'Brasil · %{x}<br>%{y:.1f}% dos alunos<extra></extra>',
        },
      ], {
        ...BL,
        height: 290,
        barmode: 'group',
        bargap: 0.24,
        bargroupgap: 0.06,
        hoverlabel: { bgcolor: '#fff', bordercolor: C.borda, font: { size: 11 } },
        showlegend: false,
        margin: { l: 44, r: 12, t: 8, b: 44 },
        xaxis: {
          title: { text: 'faixa de nota', font: { size: 10 } },
          tickfont: { size: 10 },
          tickangle: -18,
        },
        yaxis: {
          title: { text: '% dos alunos', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          ticksuffix: '%',
          rangemode: 'tozero',
        },
      }, CFG);
    }
    hArea.onchange = renderHist;
    hAno.onchange = renderHist;
    renderHist();

    const crePalette = [
      '#0A4D8C', '#2EAD6E', '#F07A28', '#F2C230', '#D6453D', '#6B4A9F',
      '#3BA4E8', '#1ABC9C', '#9B59B6', '#E67E22', '#34495E', '#16A085',
    ];
    const creList = [...new Set(DISP.map((e) => e.cre).filter(Boolean))].sort((a, b) => {
      if (a === 'CRE Campo Grande' || a === 'Campo Grande' || a === 'SED') return -1;
      if (b === 'CRE Campo Grande' || b === 'Campo Grande' || b === 'SED') return 1;
      return a.localeCompare(b, 'pt-BR');
    });
    const creColors = {};
    creList.forEach((c, i) => { creColors[c] = crePalette[i % crePalette.length]; });

    const dispCre = document.getElementById('dispCre');
    const dispZeroMode = document.getElementById('dispZeroMode');
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
        o.textContent = cre;
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
          + `<span class="disp-chip-dot"></span>${cre}</button>`;
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
            customdata: sub.map((e) => [e.mun, e.n, e.tx]),
            mode: 'markers',
            type: 'scatter',
            name: cre,
            marker: {
              size: sub.map((e) => bubbleSize(e.n || 1)),
              color: creColors[cre],
              opacity: 0.78,
              line: { color: '#fff', width: 1.4 },
            },
            hovertemplate: '<b>%{text}</b><br>%{customdata[0]}<br>CRE: '
              + `${cre}<br>Participantes: %{customdata[1]}<br>Participa\u00e7\u00e3o: %{customdata[2]:.1f}%<br>M\u00e9dia: %{y:.1f}<extra></extra>`,
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

      Plotly.react('g_dispersao', traces, {
        ...BL,
        height: 360,
        hoverlabel: { bgcolor: '#fff', bordercolor: C.borda, font: { size: 11 } },
        showlegend: false,
        margin: { l: 50, r: 16, t: 12, b: 48 },
        xaxis: {
          title: { text: 'participa\u00e7\u00e3o efetiva (%)', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          zeroline: false,
          range: [0, xMax],
          ticksuffix: '%',
          dtick: xMax > 130 ? 25 : 20,
        },
        yaxis: {
          title: { text: 'm\u00e9dia geral', font: { size: 10 } },
          gridcolor: 'rgba(0,0,0,0)',
          zeroline: false,
          range: [Math.max(300, yMin), Math.min(650, yMax)],
        },
        shapes,
        annotations,
      }, CFGI);

      if (dispCaption) {
        const nOver = pts.filter((e) => (e.tx ?? 0) > 100).length;
        const creLbl = creFilter || 'todas as CREs';
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
    if (dispZeroMode && ED.setSchoolZeroMode) dispZeroMode.value = ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all';
    document.addEventListener('enemdash:schoolZeroMode', () => {
      renderBoxplots();
      renderHist();
      renderDisp();
    });
    renderDisp();
  };
})(window.EnemDash);
