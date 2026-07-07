(function (ED) {
  const C = {
    azul: '#0A4D8C', azulEsc: '#053B71', brasil: '#8A9BB0', verde: '#2EAD6E',
    laranja: '#F07A28', dourado: '#F2C230', critico: '#D6453D', roxo: '#6B4A9F',
    azulC: '#3BA4E8', muted: '#5A718A', borda: '#CDD8E8', subtle: '#F2F6FB',
    txt: '#0A2540', txt2: '#2A4562',
  };
  const BL = {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: '#FFFFFF',
    font: { family: 'Segoe UI, system-ui, sans-serif', size: 12, color: C.txt2 },
    margin: { l: 46, r: 14, t: 8, b: 34 },
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
    bordercolor: '#CDD8E8',
    font: { family: 'Segoe UI, system-ui, sans-serif', size: 13, color: '#0A2540' },
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
    HOVER, XSPIKE, YSPIKE, PANDEMIA, layoutLineChart, layoutUnifiedY, hoverAreaTemplate, mergePandemia,
  };
})(window.EnemDash = window.EnemDash || {});
