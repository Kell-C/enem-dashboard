(function (ED) {
  const C = {
    azul: '#0C4A7A', azulEsc: '#082F4F', brasil: '#7A8FA6', verde: '#268A58',
    laranja: '#D96A1A', dourado: '#C99210', critico: '#C23D36', roxo: '#5E4588',
    azulC: '#4BA3EF', muted: '#5A6D82', borda: '#C5D4E6', subtle: '#F5F8FC',
    plotBg: '#EEF4FA', txt: '#0B1F33', txt2: '#2E4058',
  };
  const BL = {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: C.plotBg,
    font: { family: '"Plus Jakarta Sans", "Segoe UI", system-ui, sans-serif', size: 12, color: C.txt2 },
    margin: { l: 46, r: 28, t: 8, b: 34 },
  };
  const CFG = {
    displayModeBar: false,
    displaylogo: false,
    responsive: true,
    scrollZoom: false,
    doubleClick: false,
  };
  const CFG_INTERACTIVE = {
    ...CFG,
    displayModeBar: true,
    doubleClick: 'reset+autosize',
    modeBarButtonsToRemove: [
      'select2d', 'lasso2d', 'hoverClosestCartesian', 'hoverCompareCartesian',
      'toggleSpikelines', 'zoom3d', 'pan3d', 'orbitRotation', 'tableRotation',
      'resetCameraDefault3d', 'resetCameraLastSave3d', 'hoverClosest3d',
      'hoverClosestGl2d', 'hoverClosestGeo', 'sendDataToCloud',
    ],
    toImageButtonOptions: {
      format: 'png',
      filename: 'painel-enem-ms',
      scale: 2,
    },
  };
  const AREAKEYS = ['CN', 'CH', 'LC', 'MT', 'RED'];
  const AREANOME = {
    CN: 'Ci\u00eancias Nat.', CH: 'Ci\u00eancias Hum.', LC: 'Linguagens',
    MT: 'Matem\u00e1tica', RED: 'Reda\u00e7\u00e3o',
  };
  const AREANOME_FULL = {
    LC: 'Linguagens', CH: 'Ci\u00eancias Humanas', CN: 'Ci\u00eancias da Natureza',
    MT: 'Matem\u00e1tica', RED: 'Reda\u00e7\u00e3o',
  };
  const ACOR = {
    CN: C.verde, CH: C.dourado, LC: C.azulC, MT: C.critico, RED: C.roxo,
  };
  const HOVER = {
    bgcolor: '#FFFFFF',
    bordercolor: C.borda,
    font: { family: '"Plus Jakarta Sans", "Segoe UI", system-ui, sans-serif', size: 13, color: C.txt },
    align: 'left',
  };
  const XSPIKE = {
    showspikes: true,
    spikemode: 'across',
    spikesnap: 'cursor',
    spikecolor: '#CBD5E1',
    spikethickness: 1,
    spikedash: 'dot',
  };
  const YSPIKE = { ...XSPIKE };
  function layoutLineChart(extra = {}) {
    const noGrid = { gridcolor: 'rgba(0,0,0,0)', showgrid: false, zeroline: false };
    const xaxis = { ...noGrid, ...XSPIKE, ...(extra.xaxis || {}) };
    const yaxis = { ...noGrid, ...(extra.yaxis || {}) };
    const { xaxis: _xa, yaxis: _ya, ...rest } = extra;
    return {
      ...BL,
      hovermode: 'x unified',
      hoverdistance: 24,
      spikedistance: -1,
      hoverlabel: { ...HOVER, ...(rest.hoverlabel || {}) },
      xaxis,
      yaxis,
      ...rest,
    };
  }
  function layoutUnifiedY(extra = {}) {
    const yaxis = { ...YSPIKE, ...(extra.yaxis || {}) };
    const { yaxis: _ya, ...rest } = extra;
    return {
      ...BL,
      hovermode: 'y unified',
      hoverdistance: 24,
      spikedistance: -1,
      hoverlabel: { ...HOVER, ...(rest.hoverlabel || {}) },
      yaxis,
      ...rest,
    };
  }
  function hoverAreaTemplate(name, val = '%{y:.0f}') {
    return `${name}: ${val}<extra></extra>`;
  }
  /** Hover unificado: cabeçalho = ano; cada série = "Nome: valor" (legenda por cor). */
  function hoverAreaScore(name, decimals = 0) {
    const val = decimals > 0 ? `%{y:.${decimals}f}` : '%{y:.0f}';
    return hoverAreaTemplate(name, val);
  }
  const PANDEMIA = {
    x0: 2019.6,
    x1: 2021.4,
    fill: 'rgba(120,135,148,.10)',
    label: 'pandemia',
  };
  function mergePandemia(layout, opts = {}) {
    const {
      y0, y1, anos, annotate = true, yPad = 1, x0, x1, yref = 'y', xref = 'x',
    } = opts;
    const shapes = [...(layout.shapes || [])];
    const annotations = [...(layout.annotations || [])];
    if (y0 != null && y1 != null) {
      shapes.push({
        type: 'rect',
        x0: x0 ?? PANDEMIA.x0,
        x1: x1 ?? PANDEMIA.x1,
        y0,
        y1,
        xref,
        yref,
        fillcolor: PANDEMIA.fill,
        line: { width: 0 },
        layer: 'below',
      });
      if (annotate && yref === 'y') {
        const ax = x0 != null && x1 != null ? (x0 + x1) / 2 : 2020.5;
        annotations.push({
          x: ax,
          y: y1 - yPad,
          text: PANDEMIA.label,
          showarrow: false,
          font: { size: 9, color: C.muted },
        });
      }
    } else if (anos && anos.length > 1) {
      const a0 = anos[0];
      const a1 = anos[anos.length - 1];
      const span = a1 - a0 || 1;
      const px0 = Math.max(0, (2019.5 - a0) / span);
      const px1 = Math.min(1, (2021.5 - a0) / span);
      if (px1 > px0) {
        shapes.push({
          type: 'rect',
          xref: 'paper',
          yref: 'paper',
          x0: px0,
          x1: px1,
          y0: 0,
          y1: 1,
          fillcolor: PANDEMIA.fill,
          line: { width: 0 },
          layer: 'below',
        });
      }
    }
    return { ...layout, shapes, annotations };
  }
  ED.Config = {
    C, BL, CFG, CFG_INTERACTIVE, AREAKEYS, AREANOME, AREANOME_FULL, ACOR,
    HOVER, XSPIKE, YSPIKE, PANDEMIA, layoutLineChart, layoutUnifiedY, hoverAreaTemplate, hoverAreaScore, mergePandemia,
    /** Google Analytics 4 — Measurement ID (G-XXXXXXXXXX). Alternativa: meta name="enem-ga4-id" em index.html */
    GA4_MEASUREMENT_ID: '',
    /** true = não envia eventos em localhost (recomendado em desenvolvimento) */
    GA4_SKIP_LOCALHOST: true,
    /** true = envia só traffic_class=external (owner/cursor/bot ficam de fora) */
    GA4_ONLY_EXTERNAL: false,
    /** false = também envia eventos classificados como bot (com tag traffic_class=bot) */
    GA4_SKIP_BOTS: false,
  };
})(window.EnemDash = window.EnemDash || {});
