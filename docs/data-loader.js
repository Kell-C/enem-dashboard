if(location.protocol==='file:'){
  showFileWarning();
} else {
  const s = document.createElement('script');
  s.src = './data/painel_data.js?v=26';
  s.onload = () => {
    if (window.bootDashboard && typeof Plotly !== 'undefined') window.bootDashboard();
  };
  s.onerror = () => {
    showFileWarning();
    const p = document.querySelector('.file-warn-box p:last-child');
    if(p) p.innerHTML = '<b style="color:var(--critico)">Erro ao carregar painel_data.js.</b> Regenerar com <code>python scripts/gerar_web_data.py</code> ou usar <code>bash abrir_painel.sh</code>.';
  };
  document.head.appendChild(s);
}
