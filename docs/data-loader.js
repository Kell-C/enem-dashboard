if(location.protocol==='file:'){
  showFileWarning();
} else {
  let loaded = 0;
  const tryBoot = () => {
    loaded += 1;
    if (loaded >= 2 && window.bootDashboard && typeof Plotly !== 'undefined') window.bootDashboard();
  };
  const s1 = document.createElement('script');
  s1.src = './data/painel_data.js?v=27';
  s1.onload = tryBoot;
  s1.onerror = () => {
    showFileWarning();
    const p = document.querySelector('.file-warn-box p:last-child');
    if(p) p.innerHTML = '<b style="color:var(--critico)">Erro ao carregar painel_data.js.</b> Regenerar com <code>python scripts/gerar_web_data.py</code> ou usar <code>bash abrir_painel.sh</code>.';
  };
  document.head.appendChild(s1);
  const s2 = document.createElement('script');
  s2.src = './data/ranking_escolas_2025.js?v=4';
  s2.onload = tryBoot;
  s2.onerror = () => { window.RANKING_ESCOLAS_2025 = null; tryBoot(); };
  document.head.appendChild(s2);
}
