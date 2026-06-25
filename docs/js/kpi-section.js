(function (ED) {
  ED.initKpi = function (ctx) {
    const {
      ANOS, LAST_YEAR, PREV_YEAR, MED_MS, TX_MS, RANK_MS, GAP, DATA, FMT, NF, trendTag,
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
    document.getElementById('kpiPartVal').textContent = tx != null ? `${FMT(tx)}%` : '\u2014';
    const N = DATA.estadualN[i];
    const Cc = DATA.estadualConcl[i];
    const vale = TX_MS.reduce((b, v) => (v != null && (b == null || v < b) ? v : b), null);
    const valeYear = vale != null ? ANOS[TX_MS.indexOf(vale)] : '\u2014';
    document.getElementById('kpiPartSub').innerHTML =
      `${LAST_YEAR} \u00b7 <b>${NF(N)}</b> participantes efetivos de <b>${NF(Cc)}</b> concluintes \u00b7 vale ${FMT(vale)}% em ${valeYear}`;
    document.getElementById('kpiRankVal').innerHTML =
      rk != null ? `${rk}\u00ba<span style="font-size:14px;color:var(--muted)">/27</span>` : '\u2014';
    const rkDelta = rkPrev != null && rk != null ? rkPrev - rk : null;
    const tRk = trendTag(rkDelta, false);
    document.getElementById('kpiRankSub').innerHTML =
      `${LAST_YEAR} \u00b7 <span class="${tRk.cls}">${tRk.txt}</span> desde ${PREV_YEAR} (${rkPrev != null ? `${rkPrev}\u00ba` : '\u2014'})`;
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

    const f = DATA.funil2024 && DATA.funil2024.Estadual;
    if (f) {
      const nf = (n) => n.toLocaleString('pt-BR');
      const pc = (n) => `${(100 * n / f.concluintes).toFixed(0)}%`;
      const st = [
        { k: 'Concluintes do EM', v: f.concluintes, p: 'universo da rede (matr\u00edcula)', hl: false },
        { k: 'Inscritos no ENEM', v: f.inscritos, p: `${pc(f.inscritos)} dos concluintes`, hl: false },
        { k: 'Presentes nos 2 dias de prova', v: f.presentes, p: `${pc(f.presentes)} dos concluintes`, hl: false },
        { k: 'Participantes efetivos', v: f.presfilt, p: `${pc(f.presfilt)} = participa\u00e7\u00e3o efetiva`, hl: true },
      ];
      document.getElementById('fstages').innerHTML = st.map((s) =>
        `<div class="fstage${s.hl ? ' hl' : ''}"><div class="fk">${s.k}</div><div class="fv">${nf(s.v)}</div><div class="fp">${s.p}</div></div>`
      ).join('');
    }
  };
})(window.EnemDash);
