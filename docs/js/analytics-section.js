(function (ED) {
  const TAB_NAMES = {
    'tab-ranking': 'Ranking',
    'tab-panorama': 'Indicadores',
    'tab-territorio': 'Território',
    'tab-distribuicao': 'Distribuição',
    'tab-redes': 'Redes',
    'tab-consistencia': 'Consistência',
    'tab-integridade': 'Integridade',
    'tab-analytics': 'Analytics',
  };

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function fmtNum(n) {
    if (n == null || Number.isNaN(n)) return '—';
    return Number(n).toLocaleString('pt-BR');
  }

  function fmtDuration(sec) {
    if (!sec) return '—';
    if (sec < 60) return `${sec}s`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return s ? `${m}m ${s}s` : `${m}m`;
  }

  function barList(items, opts = {}) {
    const max = Math.max(...items.map((i) => i.count || 0), 1);
    const labelKey = opts.labelKey || 'label';
    const countKey = opts.countKey || 'count';
    if (!items.length) return '<p class="ana-empty">Sem dados no período.</p>';
    return `<ul class="ana-barlist">${items.map((item) => {
      const pct = Math.round(((item[countKey] || 0) / max) * 100);
      const label = item.label || item[labelKey] || '—';
      return `<li><span class="ana-bar-label">${esc(label)}</span><span class="ana-bar-track"><i style="width:${pct}%"></i></span><span class="ana-bar-val">${fmtNum(item[countKey])}</span></li>`;
    }).join('')}</ul>`;
  }

  function renderKpis(totals) {
    const el = document.getElementById('anaKpis');
    if (!el || !totals) return;
    el.innerHTML = `
      <div class="kpi"><p class="lbl">Visitas</p><div class="val val-sm">${fmtNum(totals.page_views)}</div></div>
      <div class="kpi"><p class="lbl">Visitantes únicos</p><div class="val val-sm">${fmtNum(totals.unique_visitors)}</div></div>
      <div class="kpi"><p class="lbl">Sessões</p><div class="val val-sm">${fmtNum(totals.sessions)}</div></div>
      <div class="kpi"><p class="lbl">Duração média</p><div class="val val-sm">${fmtDuration(totals.avg_duration_sec)}</div></div>
      <div class="kpi"><p class="lbl">Taxa de rejeição</p><div class="val val-sm">${totals.bounce_rate ?? '—'}%</div></div>
      <div class="kpi"><p class="lbl">Retornantes</p><div class="val val-sm">${fmtNum(totals.returning_visitors)}</div></div>`;
  }

  function renderDailyChart(daily) {
    const { C, BL, CFG } = ED.Config;
    const xs = (daily || []).map((d) => d.date);
    const ys = (daily || []).map((d) => d.count);
    ED.createChart('g_ana_daily', [{
      x: xs,
      y: ys,
      type: 'bar',
      marker: { color: C.azul },
      hovertemplate: '%{x}<br>%{y} visitas<extra></extra>',
    }], {
      ...BL,
      height: 260,
      margin: { l: 44, r: 16, t: 8, b: 40 },
      xaxis: { tickangle: -35, tickfont: { size: 10 } },
      yaxis: { title: 'Visitas', rangemode: 'tozero' },
    }, CFG);
  }

  function renderHourlyChart(hourly) {
    const { C, BL, CFG } = ED.Config;
    const byHour = Array.from({ length: 24 }, (_, h) => {
      const found = (hourly || []).find((x) => x.hour === h);
      return found ? found.count : 0;
    });
    ED.createChart('g_ana_hourly', [{
      x: Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}h`),
      y: byHour,
      type: 'scatter',
      mode: 'lines+markers',
      line: { color: C.azulC, width: 2 },
      marker: { size: 5, color: C.azul },
      hovertemplate: '%{x}<br>%{y} visitas<extra></extra>',
    }], {
      ...BL,
      height: 220,
      margin: { l: 44, r: 16, t: 8, b: 36 },
      xaxis: { tickfont: { size: 10 } },
      yaxis: { rangemode: 'tozero' },
    }, CFG);
  }

  function renderTabsChart(tabs) {
    const { C, BL, CFG } = ED.Config;
    const labels = (tabs || []).map((t) => t.label || TAB_NAMES[t.id] || t.id);
    const counts = (tabs || []).map((t) => t.count);
    ED.createChart('g_ana_tabs', [{
      y: labels,
      x: counts,
      type: 'bar',
      orientation: 'h',
      marker: { color: C.verde },
      hovertemplate: '%{y}<br>%{x} visualizações<extra></extra>',
    }], {
      ...BL,
      height: Math.max(220, labels.length * 34),
      margin: { l: 140, r: 16, t: 8, b: 32 },
      xaxis: { rangemode: 'tozero' },
      yaxis: { automargin: true },
    }, CFG);
  }

  function renderSessions(rows) {
    const el = document.getElementById('anaSessionsBody');
    if (!el) return;
    if (!rows?.length) {
      el.innerHTML = '<tr><td colspan="7">Nenhuma sessão registrada.</td></tr>';
      return;
    }
    el.innerHTML = rows.map((s) => `
      <tr>
        <td>${esc((s.started_at || '').replace('T', ' ').slice(0, 16))}</td>
        <td>${esc(s.device)}</td>
        <td>${esc(s.browser)}</td>
        <td>${fmtDuration(s.duration_sec)}</td>
        <td>${fmtNum(s.tabs)}</td>
        <td>${fmtNum(s.events)}</td>
        <td>${s.returning ? 'Retorno' : 'Novo'}</td>
      </tr>`).join('');
  }

  function showStatus(kind, message) {
    const el = document.getElementById('anaStatus');
    if (!el) return;
    el.className = `ana-status ana-status-${kind}`;
    el.textContent = message;
    el.hidden = !message;
  }

  function loadSummary(days) {
    showStatus('loading', 'Carregando dados de analytics…');
    return fetch(`/api/analytics/summary?days=${days}`)
      .then((r) => {
        if (!r.ok) throw new Error('summary_failed');
        return r.json();
      })
      .then((data) => {
        showStatus('ok', `Atualizado em ${new Date(data.generated_at).toLocaleString('pt-BR')} · últimos ${data.period_days} dias`);
        renderKpis(data.totals);
        renderDailyChart(data.daily_visits);
        renderHourlyChart(data.hourly_visits);
        renderTabsChart(data.tabs);
        document.getElementById('anaDevices').innerHTML = barList(data.devices);
        document.getElementById('anaReferrers').innerHTML = barList(data.referrers);
        document.getElementById('anaSchools').innerHTML = barList(data.schools);
        document.getElementById('anaTerritory').innerHTML = barList(
          [...(data.cre || []), ...(data.municipios || [])].slice(0, 10),
        );
        document.getElementById('anaFilters').innerHTML = barList(data.filters);
        renderSessions(data.recent_sessions);
      })
      .catch(() => {
        showStatus('warn', 'Coleta indisponível neste host. No GitHub Pages só o painel estático é publicado — use bash abrir_painel.sh localmente ou hospede scripts/serve_painel.py em um servidor com Python.');
        renderKpis(null);
        ['anaDevices', 'anaReferrers', 'anaSchools', 'anaTerritory', 'anaFilters'].forEach((id) => {
          const node = document.getElementById(id);
          if (node) node.innerHTML = '<p class="ana-empty">—</p>';
        });
        renderSessions([]);
      });
  }

  function initAnalyticsSection() {
    const panel = document.getElementById('tab-analytics');
    if (!panel || panel.dataset.ready) return;
    panel.dataset.ready = '1';

    const periodSel = document.getElementById('anaPeriod');
    const refreshBtn = document.getElementById('anaRefresh');

    const refresh = () => loadSummary(Number(periodSel?.value || 30));
    refreshBtn?.addEventListener('click', refresh);
    periodSel?.addEventListener('change', refresh);

    document.addEventListener('dash-tab-show', (e) => {
      if (e.detail?.id === 'tab-analytics') refresh();
    });

    if (panel.classList.contains('is-active') && !panel.hidden) refresh();
  }

  ED.initAnalyticsSection = initAnalyticsSection;
})(window.EnemDash = window.EnemDash || {});
