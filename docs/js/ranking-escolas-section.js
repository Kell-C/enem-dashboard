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
    const vals = [];
    AREA_KEYS.forEach((k) => { (h[k] || []).forEach((v) => { if (v != null && !Number.isNaN(v)) vals.push(v); }); });
    (h.media || []).forEach((v) => { if (v != null && !Number.isNaN(v)) vals.push(v); });
    if (!vals.length) return [400, 650];
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const pad = Math.max(8, (hi - lo) * 0.08);
    return [Math.floor(lo - pad), Math.ceil(hi + pad)];
  }

  function renderHistChart(escola) {
    const plotEl = document.getElementById('rankEscHistPlot');
    const title = document.getElementById('rankEscHistTitle');
    const sub = document.getElementById('rankEscHistSub');
    const mediaEl = document.getElementById('rankEscDetailMedia');
    if (!plotEl || !escola?.historico?.anos?.length) return;

    const { C, CFG, AREANOME_FULL, ACOR, layoutLineChart, hoverAreaTemplate } = ED.Config;
    const h = escola.historico;
    const anoMin = Math.min(...h.anos);
    const anoMax = Math.max(...h.anos);

    if (title) title.textContent = escola.nome;
    if (sub) sub.textContent = `${escola.municipio} · INEP ${escola.coInep}`;
    if (mediaEl) mediaEl.textContent = fmtNum(escola.mediaGeral);
    renderPosicoes(escola);

    const traces = AREA_KEYS.map((k) => {
      const name = AREANOME_FULL[k] || k;
      return {
        x: h.anos,
        y: h[k],
        mode: 'lines+markers',
        name,
        line: { color: ACOR[k], width: 2.5 },
        marker: { size: 6, line: { width: 0 } },
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
      layoutLineChart({
        height: 340,
        margin: { l: 48, r: 20, t: 16, b: 44 },
        xaxis: {
          title: '',
          dtick: 2,
          tickmode: 'linear',
          range: [anoMin - 0.5, anoMax + 0.5],
          gridcolor: '#F0F1F6',
          linecolor: '#E5E7EF',
          tickfont: { size: 12, color: '#6B7280' },
        },
        yaxis: {
          title: 'Nota TRI',
          range: [yMin, yMax],
          dtick: 20,
          gridcolor: '#F0F1F6',
          linecolor: '#E5E7EF',
          tickfont: { size: 12, color: '#6B7280' },
        },
        legend: { orientation: 'h', y: 1.18, x: 0, font: { size: 11, color: '#6B7280' } },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#FFFFFF',
      }),
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
    if (!data || !Array.isArray(data.escolas) || !data.escolas.length) {
      host.querySelector('.rank-empty')?.classList.add('on');
      return;
    }

    const escolaMap = new Map(data.escolas.map((e) => [String(e.coInep), e]));
    let selectedInep = null;

    const meta = host.querySelector('#rankEscMeta');
    if (meta) {
      const anos = data.anosHistorico?.length
        ? `${data.anosHistorico[0]}–${data.anosHistorico[data.anosHistorico.length - 1]}`
        : '2013–2025';
      meta.textContent = `${data.totalEscolas} escolas estaduais · ENEM ${data.ano} · histórico ${anos} · ${FONTE}`;
    }

    const munSel = host.querySelector('#rankEscMunicipio');
    const search = host.querySelector('#rankEscSearch');
    const sortSel = host.querySelector('#rankEscSort');
    const tbody = host.querySelector('#rankEscBody');
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
        renderHistChart(escola);
        document.getElementById('rankEscDetailView')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
        const msMun = e.estaduaisMs?.municipio;
        const msUf = e.estaduaisMs?.uf;
        const brEst = e.estaduaisBr?.brasil;
        return `<tr class="rk-row${tr}${sel}" data-inep="${e.coInep}" tabindex="0" role="button" aria-label="Ver detalhes de ${escHtml(e.nome)}">
        <td class="rk-pos">${i + 1}</td>
        <td class="rk-nome"><span class="b">${escHtml(e.nome)}</span><span class="rk-sub">${escHtml(e.municipio)} · INEP ${e.coInep}</span></td>
        <td class="rk-num">${fmtNum(e.mediaGeral)}</td>
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
