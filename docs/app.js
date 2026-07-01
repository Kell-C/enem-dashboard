function showFileWarning() {
  document.body.innerHTML = '<div class="file-warn"><div class="file-warn-box">'
    + '<h2>Abra pelo servidor local, não pelo arquivo</h2>'
    + '<p>O navegador bloqueia o carregamento de <code>painel_data.js</code> quando você abre o HTML direto (<code>file://</code>). Por isso a página trava e os gráficos não aparecem.</p>'
    + '<p>Use o script abaixo na pasta do painel:</p>'
    + '<span class="cmd">bash abrir_painel.sh</span>'
    + '<p>Depois abra <a href="http://127.0.0.1:8765/index.html">http://127.0.0.1:8765/index.html</a>.</p>'
    + '</div></div>';
}

function updateMethodologyBar(ED) {
  const popHint = document.getElementById('methodPopHint');
  const zeroHint = document.getElementById('methodZeroHint');
  const explain = document.getElementById('methodExplain');
  const scope = document.getElementById('methodScope');
  if (!popHint || !zeroHint || !explain || !scope) return;

  const porArea = ED.getPopulationMode && ED.getPopulationMode() === 'por_area';
  const noZero = ED.getSchoolZeroMode && ED.getSchoolZeroMode() === 'no_zero';

  if (porArea) {
    popHint.textContent = 'Para cada área, entram todos os concluintes que entregaram aquela prova — mesmo quem faltou ao outro dia ou foi eliminado em CN/MT. Compatível com ENEM por Escola / AIO.';
  } else {
    popHint.textContent = 'Mesma base de alunos para as 5 áreas: quem terminou o ENEM (presente em CN, CH, LC, MT e não eliminado).';
  }

  if (noZero) {
    zeroHint.textContent = 'Participantes com qualquer nota zero (objetivas ou redação em branco) são removidos da base.';
  } else {
    zeroHint.textContent = 'Redação em branco/cópia (nota 0) e demais zeros objetivos permanecem na média.';
  }

  const popLabel = porArea ? 'Por prova' : 'Geral (2 dias)';
  const zeroLabel = noZero ? 'sem zeros' : 'com zeros';
  explain.innerHTML = '<b>Como ler:</b> estes filtros são <b>globais</b> — alteram simultaneamente trajetória, índice por área, distribuição, snapshot, drill-down territorial (CRE/município), desvio/CV e tabelas de escola. '
    + `Combinação ativa: <b>${popLabel}</b> · <b>${zeroLabel}</b>. `
    + 'KPIs, funil, trajetória conjunta, bump chart, evolução MS×Brasil, comparação entre redes e integridade mantêm população fixa (presentes nos 2 dias).';

  if (porArea) {
    scope.innerHTML = 'Metodologias diferentes respondem perguntas diferentes: <b>Por prova</b> mede a média de cada prova entre quem a <em>entregou</em> (como ENEM por Escola / AIO) — CH, LC e Redação costumam divergir do modo Geral. <b>Geral</b> mede quem <em>terminou</em> o exame inteiro.';
  } else {
    scope.innerHTML = 'Metodologias diferentes respondem perguntas diferentes: <b>Geral</b> mede quem <em>terminou</em> o exame (presente nos 2 dias, sem eliminação). <b>Por prova</b> inclui quem entregou cada prova isoladamente — alinhado ao ENEM por Escola / AIO.';
  }
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

  document.querySelectorAll('[data-population-mode]').forEach((el) => {
    el.addEventListener('change', (e) => {
      ED.setPopulationMode(e.target.value);
      updateMethodologyBar(ED);
    });
  });
  document.querySelectorAll('[data-school-zero-mode]').forEach((el) => {
    el.addEventListener('change', (e) => {
      ED.setSchoolZeroMode(e.target.value);
      updateMethodologyBar(ED);
    });
  });
  document.addEventListener('enemdash:populationMode', () => updateMethodologyBar(ED));
  document.addEventListener('enemdash:schoolZeroMode', () => updateMethodologyBar(ED));
  if (ED.setPopulationMode) ED.setPopulationMode(ED.getPopulationMode ? ED.getPopulationMode() : 'geral');
  if (ED.setSchoolZeroMode) ED.setSchoolZeroMode(ED.getSchoolZeroMode ? ED.getSchoolZeroMode() : 'all');
  updateMethodologyBar(ED);

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
