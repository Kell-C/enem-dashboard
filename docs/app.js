function showFileWarning() {
  document.body.innerHTML = '<div class="file-warn"><div class="file-warn-box">'
    + '<h2>Abra pelo servidor local, não pelo arquivo</h2>'
    + '<p>O navegador bloqueia o carregamento de <code>painel_data.js</code> quando você abre o HTML direto (<code>file://</code>). Por isso a página trava e os gráficos não aparecem.</p>'
    + '<p>Use o script abaixo na pasta do painel:</p>'
    + '<span class="cmd">bash abrir_painel.sh</span>'
    + '<p>Depois abra <a href="http://127.0.0.1:8765/index.html">http://127.0.0.1:8765/index.html</a>.</p>'
    + '</div></div>';
}

function applyDynamicStaticText(ctx) {
  const anos = Array.isArray(ctx.ANOS) && ctx.ANOS.length ? ctx.ANOS : [2019, 2020, 2021, 2022, 2023, 2024];
  const startYear = anos[0];
  const lastYear = anos[anos.length - 1];
  const prevYear = anos[Math.max(0, anos.length - 2)];
  const recentStart = anos[Math.max(0, anos.length - 4)];
  const schoolStart = anos.find((ano) => ano >= 2024) ?? lastYear;
  const values = {
    startYear: String(startYear),
    lastYear: String(lastYear),
    prevYear: String(prevYear),
    range: `${startYear}–${lastYear}`,
    rangeAscii: `${startYear}-${lastYear}`,
    rangeText: `${startYear} a ${lastYear}`,
    recentRange: `${recentStart}–${lastYear}`,
    schoolRange: schoolStart === lastYear ? String(lastYear) : `${schoolStart}–${lastYear}`,
    fileRange: `${startYear} a ${lastYear}`,
  };

  document.title = `Painel ENEM MS — ${values.rangeAscii}`;

  document.querySelectorAll('[data-dyn]').forEach((el) => {
    const key = el.getAttribute('data-dyn');
    if (key && Object.prototype.hasOwnProperty.call(values, key)) {
      el.textContent = values[key];
    }
  });

  const periodoSelect = document.getElementById('periodoSelect');
  if (periodoSelect) {
    periodoSelect.innerHTML = '';
    [values.range, values.recentRange].forEach((label) => {
      const option = document.createElement('option');
      option.textContent = label;
      periodoSelect.appendChild(option);
    });
  }

  const snapAno = document.getElementById('snapAno');
  if (snapAno) {
    snapAno.innerHTML = '';
    [...anos].reverse().forEach((ano) => {
      const option = document.createElement('option');
      option.value = String(ano);
      option.textContent = String(ano);
      snapAno.appendChild(option);
    });
    snapAno.value = String(lastYear);
  }
}

function bootDashboard() {
  if (bootDashboard._done) return;
  bootDashboard._done = true;
  const ED = window.EnemDash;
  const ctx = ED.createContext(window.PAINEL_DATA || {});

  applyDynamicStaticText(ctx);

  if (ED.initRankingEscolas) ED.initRankingEscolas();
  ED.initAreaDetail(ctx);
  ED.initKpi(ctx);
  ED.initTrajectory(ctx);

  ED.lazySection(1, () => ED.initDrill(ctx));
  ED.lazySection(2, () => ED.initStats(ctx));
  ED.lazySection(3, () => ED.initRedes(ctx));
  ED.lazySection(4, () => ED.initCv(ctx));
  ED.lazySection(5, () => ED.initInteg(ctx));
  ED.lazyDetails('details.more', () => ED.initSnapshot(ctx));
}

function tryBootDashboard() {
  if (window.PAINEL_DATA && typeof Plotly !== 'undefined') bootDashboard();
}

window.bootDashboard = bootDashboard;
tryBootDashboard();
