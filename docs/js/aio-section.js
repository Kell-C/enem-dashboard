(function (ED) {
  const AIO_ANOS = () => (window.AIO_DATA && window.AIO_DATA.anos) || [];
  let _ctx = null;
  let _selId = null;

  function aioReady() {
    return window.AIO_DATA && window.AIO_DATA.escolas && Object.keys(window.AIO_DATA.escolas).length > 0;
  }

  function escolasList() {
    const data = window.AIO_DATA || {};
    return (data.ranking2025 || []).slice().sort((a, b) => (a.rankCalc || 999) - (b.rankCalc || 999));
  }

  function renderRanking(ctx) {
    const tbody = document.getElementById('aioRankBody');
    const note = document.getElementById('aioRankNota');
    if (!tbody) return;

    const rows = escolasList().filter((r) => (r.dependencia || 'Estadual') === 'Estadual');
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="13">Sem dados AIO. Execute <code>baixar_aio_escolas.py</code> e <code>gerar_aio_web_data.py</code>.</td></tr>';
      if (note) note.textContent = '';
      return;
    }

    tbody.innerHTML = rows.map((r, i) => {
      const rank = r.rankCalc || i + 1;
      const sel = r.id === _selId ? ' class="is-sel"' : '';
      return `<tr data-aio-id="${r.id}"${sel}>`
        + `<td>${rank}</td>`
        + `<td>${r.nome || r.id}</td>`
        + `<td>${r.mun || '—'}</td>`
        + `<td>${r.cre || '—'}</td>`
        + `<td>${r.lc != null ? r.lc.toFixed(1) : '—'}</td>`
        + `<td>${r.ch != null ? r.ch.toFixed(1) : '—'}</td>`
        + `<td>${r.cn != null ? r.cn.toFixed(1) : '—'}</td>`
        + `<td>${r.mt != null ? r.mt.toFixed(1) : '—'}</td>`
        + `<td>${r.red != null ? r.red.toFixed(1) : '—'}</td>`
        + `<td><b>${r.geral != null ? r.geral.toFixed(1) : '—'}</b></td>`
        + `<td>${r.rankMun != null ? `#${r.rankMun}` : '—'}</td>`
        + `<td>${r.rankMs != null ? `#${r.rankMs}` : '—'}</td>`
        + `<td>${r.rankBr != null ? `#${r.rankBr}` : '—'}</td>`
        + '</tr>';
    }).join('');

    if (note) {
      note.textContent = `${rows.length} escolas estaduais MS com dados AIO 2025 · clique numa linha para ver trajetória 2013–2025 · metodologia por prova (AIO).`;
    }

    tbody.querySelectorAll('tr[data-aio-id]').forEach((tr) => {
      tr.onclick = () => {
        _selId = tr.dataset.aioId;
        renderRanking(ctx);
        renderTrajectory(ctx, _selId);
      };
    });
  }

  function renderTrajectory(ctx, schoolId) {
    const host = document.getElementById('g_aio_traj');
    const title = document.getElementById('aioTrajTitle');
    const note = document.getElementById('aioTrajNota');
    if (!host || !schoolId) return;

    const { AREAKEYS, AREANOME, ACOR, BL, CFG } = ctx;
    const esc = window.AIO_DATA.escolas[schoolId];
    if (!esc) {
      host.innerHTML = '<p class="idx-empty">Escola não encontrada nos dados AIO.</p>';
      return;
    }

    const anos = esc.anos || AIO_ANOS();
    const traces = AREAKEYS.map((k) => ({
      x: anos,
      y: (esc.areas && esc.areas[k]) || [],
      mode: 'lines+markers',
      name: AREANOME[k],
      line: { color: ACOR[k], width: k === 'RED' ? 3 : 2.2 },
      marker: { size: 7, symbol: 'circle', line: { width: 1, color: '#fff' } },
      hovertemplate: `${AREANOME[k]} %{x}<br>%{y:.1f} pts<extra></extra>`,
    }));

    const geral = esc.geral || [];
    if (geral.some((v) => v != null)) {
      traces.push({
        x: anos,
        y: geral,
        mode: 'lines',
        name: 'Média geral',
        line: { color: '#334155', width: 2, dash: 'dot' },
        hovertemplate: 'Média geral %{x}<br>%{y:.1f} pts<extra></extra>',
      });
    }

    const yVals = [];
    traces.forEach((t) => (t.y || []).forEach((v) => { if (v != null) yVals.push(v); }));
    const yMin = yVals.length ? Math.min(...yVals) - 15 : 400;
    const yMax = yVals.length ? Math.max(...yVals) + 15 : 700;

    if (title) {
      title.textContent = `${esc.nome || schoolId} · trajetória AIO (2013–2025)`;
    }
    if (note) {
      const rk = esc.ranking2025 || {};
      note.textContent = [
        esc.mun ? `Município: ${esc.mun}` : null,
        rk.ms != null ? `Ranking MS (AIO): #${rk.ms}` : null,
        rk.br != null ? `Ranking Brasil (AIO): #${rk.br}` : null,
        'Fonte: aio.com.br · média por prova',
      ].filter(Boolean).join(' · ');
    }

    Plotly.react(host, traces, {
      ...BL,
      height: 340,
      dragmode: false,
      hovermode: 'x unified',
      legend: { orientation: 'h', y: -0.18, font: { size: 10 } },
      xaxis: { dtick: 2, title: { text: 'Ano', font: { size: 10 } }, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: {
        title: { text: 'Nota média', font: { size: 10 } },
        range: [Math.max(0, yMin), yMax],
        gridcolor: 'rgba(0,0,0,0.06)',
      },
    }, CFG);
  }

  function populateSelect(ctx) {
    const sel = document.getElementById('aioEscolaSelect');
    if (!sel) return;
    const rows = escolasList();
    sel.innerHTML = rows.map((r) =>
      `<option value="${r.id}">${r.nome || r.id}${r.mun ? ` · ${r.mun}` : ''}</option>`,
    ).join('');
    sel.onchange = () => {
      _selId = sel.value;
      renderTrajectory(ctx, _selId);
      renderRanking(ctx);
    };
    if (!_selId && rows.length) _selId = rows[0].id;
    sel.value = _selId || '';
  }

  ED.initAio = function (ctx) {
    _ctx = ctx;
    const wrap = document.getElementById('aioSection');
    if (!wrap) return;

    if (!aioReady()) {
      wrap.querySelector('.aio-empty')?.classList.remove('hidden');
      return;
    }
    wrap.querySelector('.aio-empty')?.classList.add('hidden');

    populateSelect(ctx);
    renderRanking(ctx);
    renderTrajectory(ctx, _selId);

    const sec = document.getElementById('aioSecAcc');
    if (sec) {
      sec.addEventListener('toggle', () => {
        if (sec.open && _selId) {
          requestAnimationFrame(() => renderTrajectory(ctx, _selId));
        }
      });
    }
  };
})(window.EnemDash);
