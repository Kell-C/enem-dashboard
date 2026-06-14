function showFileWarning() {
  document.body.innerHTML = '<div class="file-warn"><div class="file-warn-box">'
    + '<h2>Abra pelo servidor local, não pelo arquivo</h2>'
    + '<p>O navegador bloqueia o carregamento de <code>painel_data.js</code> quando você abre o HTML direto (<code>file://</code>). Por isso a página trava e os gráficos não aparecem.</p>'
    + '<p>Use o script abaixo na pasta do painel:</p>'
    + '<span class="cmd">bash abrir_painel.sh</span>'
    + '<p>Depois abra <a href="http://127.0.0.1:8765/index.html">http://127.0.0.1:8765/index.html</a>.</p>'
    + '</div></div>';
}

function bootDashboard() {
  if (bootDashboard._done) return;
  bootDashboard._done = true;
  const ED = window.EnemDash;
  const ctx = ED.createContext(window.PAINEL_DATA || {});

  ED.initAreaDetail(ctx);
  ED.initKpi(ctx);
  ED.initTrajectory(ctx);

  ED.lazySection(1, () => ED.initRedes(ctx));
  ED.lazySection(2, () => ED.initInteg(ctx));
  ED.lazySection(3, () => ED.initStats(ctx));
  ED.lazySection(4, () => ED.initCv(ctx));
  ED.lazySection(5, () => ED.initDrill(ctx));
  ED.lazyDetails('details.more', () => ED.initSnapshot(ctx));
}

function tryBootDashboard() {
  if (window.PAINEL_DATA && typeof Plotly !== 'undefined') bootDashboard();
}

window.bootDashboard = bootDashboard;
tryBootDashboard();
