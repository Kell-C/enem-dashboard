(function (ED) {
  const AREA_TAG = { CN: 'CN', CH: 'CH', LC: 'LC', MT: 'MT', RED: 'Red.' };

  ED.initKpi = function (ctx) {
    document.querySelectorAll('#kpiMedVal,#kpiPartVal,#kpiRankVal,#kpiGapVal,#kpiElimVal,#s_media,#s_part,#s_rank,#s_gap,#s_elim,#hdrMedBadge,#hdrPartBadge,#hdrRankBadge')
      .forEach((el) => el?.classList.remove('skeleton', 'skeleton-val', 'skeleton-text', 'skeleton-spark', 'lg', 'sm'));
    const {
      ANOS, LAST_YEAR, PREV_YEAR, MED_MS, TX_MS, RANK_MS, GAP, DATA, FMT, NF, trendTag,
      AREAKEYS, AREANOME, ACOR,
    } = ctx;
    const i = ANOS.length - 1;
    const i0 = 0;
    const med = MED_MS[i];
    const med0 = MED_MS[i0];
    const tx = TX_MS[i];
    const rk = RANK_MS[i];
    const rkPrev = RANK_MS[i - 1];
    const gap = GAP[i];
    const peak = MED_MS.reduce((b, v) => (v != null && (b == null || v > b) ? v : b), null);
    const peakYear = peak != null ? ANOS[MED_MS.indexOf(peak)] : '\u2014';
    const medDelta = med != null && med0 != null ? med - med0 : null;
    const tMed = trendTag(medDelta, false);
    document.getElementById('kpiMedVal').textContent = FMT(med);
    document.getElementById('kpiMedSub').innerHTML =
      `${LAST_YEAR} \u00b7 <span class="${tMed.cls}">${tMed.txt}</span> vs ${ANOS[i0]} \u00b7 pico ${FMT(peak)} em ${peakYear}`;
    const hdrMed = document.getElementById('hdrMedBadge');
    if (hdrMed) hdrMed.textContent = med != null ? FMT(med) : '\u2014';
    document.getElementById('kpiPartVal').textContent = tx != null ? `${FMT(tx)}%` : '\u2014';
    const N = DATA.estadualN[i];
    const Cc = DATA.estadualConcl[i];
    document.getElementById('kpiPartSub').innerHTML =
      `${LAST_YEAR} \u00b7 <b>${NF(N)}</b> participantes de <b>${NF(Cc)}</b> concluintes`;
    const hdrPart = document.getElementById('hdrPartBadge');
    if (hdrPart) hdrPart.textContent = tx != null ? `${FMT(tx)}%` : '\u2014';
    document.getElementById('kpiRankVal').innerHTML =
      rk != null ? `${rk}\u00ba<span style="font-size:14px;color:var(--muted)">/27</span>` : '\u2014';
    const rkDelta = rkPrev != null && rk != null ? rkPrev - rk : null;
    const tRk = trendTag(rkDelta, false);
    document.getElementById('kpiRankSub').innerHTML =
      `${LAST_YEAR} \u00b7 <span class="${tRk.cls}">${tRk.txt}</span> desde ${PREV_YEAR} (${rkPrev != null ? `${rkPrev}\u00ba` : '\u2014'})`;
    const hdrRank = document.getElementById('hdrRankBadge');
    if (hdrRank) hdrRank.textContent = rk != null ? `${rk}\u00ba/27` : '\u2014';
    const gapCard = document.getElementById('kpiGapCard');
    const gapVal = document.getElementById('kpiGapVal');
    gapCard.classList.toggle('neg', gap != null && gap < 0);
    gapVal.textContent = gap == null ? '\u2014' : `${gap > 0 ? '+' : ''}${FMT(gap)}`;
    gapVal.style.color = gap != null && gap < 0 ? 'var(--critico)' : 'var(--azul-esc)';
    const gap22 = GAP[ANOS.indexOf(2022)];
    document.getElementById('kpiGapSub').innerHTML =
      `${LAST_YEAR} \u00b7 <span class="trend up">\u25B2 est\u00e1vel</span>${gap22 != null ? ` (era ${FMT(gap22)} em 2022)` : ''}`;
    const r0 = RANK_MS[i0];
    const rLast = RANK_MS[i];
    if (r0 != null && rLast != null) {
      const prevRank = RANK_MS[ANOS.indexOf(PREV_YEAR)];
      document.getElementById('notaBump').textContent =
        `MS passou de ${r0}\u00ba (${ANOS[i0]}) para ${prevRank}\u00ba (${PREV_YEAR}) e ficou em ${rLast}\u00ba (${LAST_YEAR}).`;
    }
    const g24 = GAP[i];
    const g22 = GAP[ANOS.indexOf(2022)];
    if (g24 != null && g22 != null) {
      document.getElementById('notaEvol').textContent =
        `A defasagem foi ${FMT(g24)} em ${LAST_YEAR} (era ${FMT(g22)} em 2022).`;
    }

    ED.spark(ctx, 's_media', MED_MS, '#0A4D8C');
    ED.spark(ctx, 's_part', TX_MS, '#2EAD6E');
    ED.spark(ctx, 's_rank', RANK_MS, '#F07A28', true);
    ED.spark(ctx, 's_gap', GAP, '#D6453D');

    const txElim = DATA.txElim || [];
    const valid = txElim.filter((v) => v != null);
    const last = valid.length ? valid[valid.length - 1] : null;
    const first = valid.length ? valid[0] : null;
    const trend = last != null && first != null
      ? (last < first ? 'down' : (last > first ? 'up' : 'stable')) : 'stable';
    const trendTxt = { down: '\u25BC reduziu', up: '\u25B2 aumentou', stable: '\u25B2 est\u00e1vel' };
    const trendCls = { down: 'trend up', up: 'trend down', stable: 'trend up' };
    document.getElementById('kpiElimVal').textContent =
      last != null ? `${last.toFixed(1).replace('.', ',')}%` : '\u2014';
    document.getElementById('kpiElimSub').innerHTML =
      `${LAST_YEAR} \u00b7 <span class="${trendCls[trend]}">${trendTxt[trend]}</span> vs ${ANOS[i0]}`;
    ED.spark(ctx, 's_elim', txElim, '#9B59B6');

    const areaHost = document.getElementById('kpiAreas');
    const msArea = DATA.msArea || {};
    if (areaHost && AREAKEYS) {
      const rangeLabel = `${ANOS[0]}\u2013${LAST_YEAR}`;
      areaHost.className = 'area-chips';
      areaHost.innerHTML = AREAKEYS.map((k) =>
        `<article class="area-chip" data-area="${k}" style="--chip-color:${ACOR[k]}">
          <header class="area-chip-head">
            <span class="area-chip-tag">${AREA_TAG[k] || k}</span>
            <span class="area-chip-name">${AREANOME[k]}</span>
          </header>
          <div class="area-chip-body">
            <span class="area-chip-val" id="kpiAreaVal_${k}">\u2014</span>
            <div class="area-chip-spark spark" id="s_area_${k}"></div>
          </div>
          <p class="area-chip-sub" id="kpiAreaSub_${k}">\u2014</p>
          <span class="help area-chip-help">i<span class="tip"><b>O que é:</b> média de ${AREANOME[k]} na população de referência (rede estadual MS). Comparação com Brasil = média entre estudantes de <b>escolas estaduais</b>. <b>Como ler:</b> valor de ${LAST_YEAR}; a linha acompanha ${rangeLabel}.</span></span>
        </article>`
      ).join('');

      AREAKEYS.forEach((k) => {
        const series = msArea[k]?.ms || [];
        const brSeries = msArea[k]?.br || [];
        const val = series[i];
        const firstIdx = series.findIndex((v) => v != null);
        const baseYear = firstIdx >= 0 ? ANOS[firstIdx] : ANOS[0];
        const val0 = firstIdx >= 0 ? series[firstIdx] : null;
        let peak = null;
        let peakYear = '\u2014';
        series.forEach((v, j) => {
          if (v != null && (peak == null || v > peak)) { peak = v; peakYear = ANOS[j]; }
        });
        const delta = val != null && val0 != null ? val - val0 : null;
        const t = trendTag(delta, false);
        const gapBr = val != null && brSeries[i] != null ? val - brSeries[i] : null;

        const valEl = document.getElementById(`kpiAreaVal_${k}`);
        const subEl = document.getElementById(`kpiAreaSub_${k}`);
        if (valEl) {
          valEl.textContent = val != null ? FMT(val) : '\u2014';
        }
        if (subEl) {
          let sub = `${LAST_YEAR} \u00b7 <span class="${t.cls}">${t.txt}</span> vs ${baseYear}`;
          if (peak != null) sub += ` \u00b7 pico ${FMT(peak)} em ${peakYear}`;
          if (gapBr != null) sub += ` \u00b7 ${gapBr >= 0 ? '+' : ''}${FMT(gapBr)} vs BR`;
          subEl.innerHTML = sub;
        }
        ED.spark(ctx, `s_area_${k}`, series, ACOR[k]);
      });
    }

    const f = DATA.funil2024 && DATA.funil2024.Estadual;
    const funnelHost = document.getElementById('fstages');
    if (f && funnelHost) {
      const nf = (n) => n.toLocaleString('pt-BR');
      const base = f.concluintes || 1;
      const pc = (n) => `${(100 * n / base).toFixed(0)}%`;
      const st = [
        { k: 'Concluintes do EM', v: f.concluintes, p: 'universo da rede (matr\u00edcula)', hl: false },
        { k: 'Inscritos no ENEM', v: f.inscritos, p: `${pc(f.inscritos)} dos concluintes`, hl: false },
        { k: 'Presentes em ao menos uma \u00e1rea', v: f.presentes, p: `${pc(f.presentes)} dos concluintes`, hl: false },
        { k: 'Participantes nos 2 dias', v: f.presentes_2d, p: `${pc(f.presentes_2d)} dos concluintes \u00b7 sem elimina\u00e7\u00e3o`, hl: true },
      ];
      funnelHost.className = 'fstages fstages-funnel';
      funnelHost.innerHTML = st.map((s) => {
        const pct = Math.round((100 * s.v) / base);
        const flex = Math.max(0.55, s.v / base).toFixed(3);
        return `<div class="fstage${s.hl ? ' hl' : ''}" style="--stage-flex:${flex};--stage-pct:${pct}">
          <div class="fstage-bar" aria-hidden="true"><i style="width:${pct}%"></i></div>
          ${s.hl ? '<span class="fstage-badge">Participa\u00e7\u00e3o efetiva</span>' : ''}
          <div class="fk">${s.k}</div>
          <div class="fv">${nf(s.v)}</div>
          <div class="fp">${s.p}</div>
        </div>`;
      }).join('');
    }
  };
})(window.EnemDash);
