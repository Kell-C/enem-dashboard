(function (ED) {
  const TOP_N = 15;
  const AREA_KEYS = ['LC', 'CH', 'CN', 'MT', 'RED'];
  const FONTE = 'Microdados INEP / ENEM';

  function fmtRank(pos, total) {
    if (pos == null || pos === '') return '—';
    if (total != null && total > 0) return `#${pos} <span class="rk-den">/ ${total}</span>`;
    return `#${pos}`;
  }

  function fmtNum(v, dec = 1) {
    if (v == null || Number.isNaN(v)) return '—';
    return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function escHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function badgeClass(pos, total) {
    if (pos == null || !total) return '';
    const q = pos / total;
    if (q <= 0.1) return 'rk-top';
    if (q <= 0.25) return 'rk-good';
    if (q >= 0.75) return 'rk-low';
    return '';
  }

  function panelRefMedias() {
    const pd = window.PAINEL_DATA || {};
    const anos = pd.anos || [];
    const i = anos.length - 1;
    if (i < 0) return { refMs: null, refBr: null };
    return {
      refMs: pd.medMs?.[i] ?? null,
      refBr: pd.medBr?.[i] ?? null,
    };
  }

  function scoreCellClass(v, refMs, refBr) {
    if (v == null || refMs == null) return '';
    if (refBr != null && v >= refBr) return 'br-ok';
    if (v >= refMs) return 'ms-ok';
    return 'bad';
  }

  function renderPosicoes(escola) {
    const el = document.getElementById('rankEscPosicoes');
    if (!el || !escola) return;
    const est = escola.estaduaisMs || {};
    const br = escola.estaduaisBr || {};
    const geral = escola.todasRedes || {};
    el.innerHTML = `
      <div class="rank-pos-group">
        <h5>Entre escolas estaduais</h5>
        <ul class="rank-pos-list">
          <li><span>Município</span><b>${fmtRank(est.municipio, est.totalMunicipio)}</b></li>
          <li><span>Mato Grosso do Sul</span><b>${fmtRank(est.uf, est.totalUf)}</b></li>
          <li><span>Brasil</span><b>${fmtRank(br.brasil, br.totalBrasil)}</b></li>
        </ul>
      </div>
      <div class="rank-pos-group">
        <h5>Entre todas as redes</h5>
        <ul class="rank-pos-list">
          <li><span>Município</span><b>${fmtRank(geral.municipio, geral.totalMunicipio)}</b></li>
          <li><span>Mato Grosso do Sul</span><b>${fmtRank(geral.uf, geral.totalUf)}</b></li>
          <li><span>Brasil</span><b>${fmtRank(geral.brasil, geral.totalBrasil)}</b></li>
        </ul>
      </div>`;
  }

  function yRangeHist(h) {
    return [0, 1000];
  }

  function renderAreaKpis(escola) {
    const host = document.getElementById('rankEscAreaKpis');
    if (!host || !escola) return;
    const { AREANOME_FULL, ACOR } = ED.Config;
    const h = escola.historico || {};
    const notas2025 = escola.notas || {};
    const idx25 = h.anos?.indexOf(2025);
    const idx24 = h.anos?.indexOf(2024);

    host.innerHTML = AREA_KEYS.map((k) => {
      const name = AREANOME_FULL[k] || k;
      const v25 = notas2025[k] ?? (idx25 >= 0 ? h[k]?.[idx25] : null);
      const v24 = idx24 >= 0 ? h[k]?.[idx24] : null;
      let trendHtml = '<span class="trend">— vs 2024</span>';
      if (v25 != null && v24 != null) {
        const d = v25 - v24;
        if (d > 0.05) {
          trendHtml = `<span class="trend up">\u25B2 +${fmtNum(d)} vs 2024</span>`;
        } else if (d < -0.05) {
          trendHtml = `<span class="trend down">\u25BC ${fmtNum(d)} vs 2024</span>`;
        } else {
          trendHtml = '<span class="trend up">\u25B2 est\u00e1vel vs 2024</span>';
        }
      }
      return `<div class="kpi kpi-area rank-area-kpi" data-area="${k}" style="--area-accent:${ACOR[k]}">
        <div class="kpi-area-bar" aria-hidden="true"></div>
        <p class="lbl">${name}</p>
        <div class="val" style="color:${ACOR[k]}">${v25 != null ? fmtNum(v25) : '—'}</div>
        <div class="vsub">${trendHtml}</div>
      </div>`;
    }).join('');
  }

  function renderHistChart(escola, refs) {
    const plotEl = document.getElementById('rankEscHistPlot');
    const title = document.getElementById('rankEscHistTitle');
    const sub = document.getElementById('rankEscHistSub');
    const mediaEl = document.getElementById('rankEscDetailMedia');
    if (!plotEl || !escola?.historico?.anos?.length) return;

    const { refMs, refBr } = refs || panelRefMedias();

    const { C, CFG, AREANOME_FULL, ACOR, layoutLineChart, hoverAreaTemplate, mergePandemia } = ED.Config;
    const axisMuted = C.txt2 || C.muted;
    const h = escola.historico;
    const anoMin = Math.min(...h.anos);
    const anoMax = Math.max(...h.anos);

    if (title) title.textContent = escola.nome;
    if (sub) sub.textContent = `${escola.municipio} · INEP ${escola.coInep}`;
    if (mediaEl) {
      mediaEl.textContent = fmtNum(escola.mediaGeral);
      mediaEl.className = scoreCellClass(escola.mediaGeral, refMs, refBr);
    }
    renderPosicoes(escola);
    renderAreaKpis(escola);

    const traces = AREA_KEYS.map((k) => {
      const name = AREANOME_FULL[k] || k;
      return {
        x: h.anos,
        y: h[k],
        mode: 'lines',
        name,
        line: { color: ACOR[k], width: 2.5 },
        connectgaps: false,
        hovertemplate: hoverAreaTemplate(name),
      };
    });

    traces.push({
      x: h.anos,
      y: h.media,
      mode: 'lines',
      name: 'Média geral',
      line: { color: C.brasil, width: 2, dash: 'dot' },
      connectgaps: false,
      hovertemplate: hoverAreaTemplate('Média geral'),
    });

    const [yMin, yMax] = yRangeHist(h);

    Plotly.newPlot(
      plotEl,
      traces,
      mergePandemia(layoutLineChart({
        height: 340,
        margin: { l: 36, r: 20, t: 16, b: 44 },
        xaxis: {
          title: '',
          dtick: 2,
          tickmode: 'linear',
          range: [anoMin - 0.5, anoMax + 0.5],
          gridcolor: 'rgba(0,0,0,0)',
          showgrid: false,
          linecolor: '#E5E7EF',
          tickfont: { size: 12, color: axisMuted },
        },
        yaxis: {
          title: { text: 'Nota TRI', font: { size: 9, color: axisMuted } },
          range: [yMin, yMax],
          dtick: 200,
          gridcolor: 'rgba(0,0,0,0)',
          showgrid: false,
          linecolor: '#E5E7EF',
          tickfont: { size: 8, color: axisMuted },
        },
        legend: { orientation: 'h', y: 1.18, x: 0, font: { size: 11, color: axisMuted } },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#FFFFFF',
      }), { y0: yMin, y1: yMax }),
      CFG,
    );
  }

  function showDetailView(on) {
    document.getElementById('rankEscListView')?.classList.toggle('hidden', on);
    document.getElementById('rankEscDetailView')?.classList.toggle('on', on);
  }

  function closeDetailView() {
    showDetailView(false);
    document.querySelectorAll('#rankEscBody tr.rk-row-sel').forEach((tr) => tr.classList.remove('rk-row-sel'));
  }

  function initRankingEscolas() {
    const data = window.RANKING_ESCOLAS_2025;
    const host = document.getElementById('rankEscSection');
    if (!host) return;
    const meta = host.querySelector('#rankEscMeta');
    const tbody = host.querySelector('#rankEscBody');
    if (!data || !Array.isArray(data.escolas) || !data.escolas.length) {
      host.querySelector('.rank-empty')?.classList.add('on');
      if (tbody) tbody.innerHTML = '';
      if (meta) meta.textContent = 'Dados de ranking não disponíveis.';
      return;
    }

    const escolaMap = new Map(data.escolas.map((e) => [String(e.coInep), e]));
    let selectedInep = null;
    const refs = panelRefMedias();

    const yearBadge = host.querySelector('#rankEscYearBadge');
    if (yearBadge) yearBadge.textContent = `ENEM ${data.ano}`;
    const scopeNote = host.querySelector('.rank-scope-note');
    if (scopeNote) {
      scopeNote.innerHTML = 'Posições entre <strong>escolas estaduais</strong> (município, MS e Brasil). '
        + `Fonte: ${FONTE}.`;
    }
    if (meta) {
      const anos = data.anosHistorico?.length
        ? `${data.anosHistorico[0]}–${data.anosHistorico[data.anosHistorico.length - 1]}`
        : '2013–2025';
      meta.innerHTML = `${data.totalEscolas} escolas estaduais · histórico ${anos} · ${FONTE}`;
    }

    const munSel = host.querySelector('#rankEscMunicipio');
    const search = host.querySelector('#rankEscSearch');
    const sortSel = host.querySelector('#rankEscSort');
    const closeBtn = document.getElementById('rankEscHistClose');
    const allRows = data.escolas;

    if (munSel) {
      munSel.innerHTML = '<option value="">Todos os municípios</option>'
        + (data.municipios || []).map((m) => `<option value="${escHtml(m)}">${escHtml(m)}</option>`).join('');
    }

    function filtered() {
      const q = (search?.value || '').trim().toLowerCase();
      const mun = munSel?.value || '';
      return allRows.filter((e) => {
        if (mun && e.municipio !== mun) return false;
        if (!q) return true;
        return e.nome.toLowerCase().includes(q)
          || e.municipio.toLowerCase().includes(q)
          || String(e.coInep).includes(q);
      });
    }

    function sortFn(key) {
      const map = {
        media: (e) => e.mediaGeral,
        ms_uf: (e) => e.estaduaisMs?.uf,
        br_est: (e) => e.estaduaisBr?.brasil,
        mun: (e) => e.municipio,
      };
      return map[key] || map.media;
    }

    function openEscola(inep) {
      const key = String(inep);
      selectedInep = key;
      const escola = escolaMap.get(key);
      document.querySelectorAll('#rankEscBody tr.rk-row').forEach((tr) => {
        tr.classList.toggle('rk-row-sel', tr.dataset.inep === key);
      });
      if (escola?.historico?.anos?.length) {
        showDetailView(true);
        renderHistChart(escola, refs);
        document.getElementById('rankEscDetailView')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        if (ED.track) {
          ED.track('school_view', {
            inep: key,
            municipio: escola.municipio || null,
            source: 'ranking',
          });
        }
      } else {
        closeDetailView();
        selectedInep = null;
      }
    }

    function renderTable(rows, sortKey) {
      const sorted = [...rows].sort((a, b) => {
        const va = sortKey(a);
        const vb = sortKey(b);
        if (va == null && vb == null) return a.nome.localeCompare(b.nome, 'pt-BR');
        if (va == null) return 1;
        if (vb == null) return -1;
        if (va !== vb) return va - vb;
        return a.nome.localeCompare(b.nome, 'pt-BR');
      });

      if (!tbody) return;
      tbody.innerHTML = sorted.map((e, i) => {
        const sel = String(e.coInep) === selectedInep ? ' rk-row-sel' : '';
        const tr = i < TOP_N ? ' rk-highlight' : '';
        const topCls = i === 0 ? ' rk-top-1' : i === 1 ? ' rk-top-2' : i === 2 ? ' rk-top-3' : '';
        const msMun = e.estaduaisMs?.municipio;
        const msUf = e.estaduaisMs?.uf;
        const brEst = e.estaduaisBr?.brasil;
        const medCls = scoreCellClass(e.mediaGeral, refs.refMs, refs.refBr);
        const posInner = i < 3
          ? `<span class="rk-pos-badge">${i + 1}</span>`
          : String(i + 1);
        return `<tr class="rk-row${tr}${topCls}${sel}" data-inep="${e.coInep}" tabindex="0" role="button" aria-label="Ver detalhes de ${escHtml(e.nome)}">
        <td class="rk-pos">${posInner}</td>
        <td class="rk-nome"><span class="b">${escHtml(e.nome)}</span><span class="rk-sub">${escHtml(e.municipio)} · INEP ${e.coInep}</span></td>
        <td class="rk-num ${medCls}">${fmtNum(e.mediaGeral)}</td>
        <td class="rk-rank ${badgeClass(msMun, e.estaduaisMs?.totalMunicipio)}">${fmtRank(msMun, e.estaduaisMs?.totalMunicipio)}</td>
        <td class="rk-rank ${badgeClass(msUf, e.estaduaisMs?.totalUf)}">${fmtRank(msUf, e.estaduaisMs?.totalUf)}</td>
        <td class="rk-rank ${badgeClass(brEst, e.estaduaisBr?.totalBrasil)}">${fmtRank(brEst, e.estaduaisBr?.totalBrasil)}</td>
      </tr>`;
      }).join('');
    }

    function refresh() {
      if (selectedInep) return;
      const rows = filtered();
      renderTable(rows, sortFn(sortSel?.value || 'ms_uf'));
    }

    tbody?.addEventListener('click', (ev) => {
      const tr = ev.target.closest('tr.rk-row');
      if (!tr?.dataset.inep) return;
      openEscola(tr.dataset.inep);
    });

    tbody?.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      const tr = ev.target.closest('tr.rk-row');
      if (!tr?.dataset.inep) return;
      ev.preventDefault();
      openEscola(tr.dataset.inep);
    });

    closeBtn?.addEventListener('click', () => {
      selectedInep = null;
      closeDetailView();
      refresh();
    });

    search?.addEventListener('input', refresh);
    munSel?.addEventListener('change', refresh);
    sortSel?.addEventListener('change', refresh);
    refresh();
  }

  ED.initRankingEscolas = initRankingEscolas;
})(window.EnemDash = window.EnemDash || {});
