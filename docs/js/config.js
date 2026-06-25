(function (ED) {
  const C = {
    azul: '#0A4D8C', azulEsc: '#053B71', brasil: '#7B8794', verde: '#2EAD6E',
    laranja: '#F07A28', dourado: '#F2C230', critico: '#D6453D', roxo: '#6B4A9F',
    azulC: '#3BA4E8', muted: '#475569', borda: '#B8C4D4', subtle: '#E8EDF3',
  };
  const BL = {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: '#FFFFFF',
    font: { family: 'Segoe UI, system-ui, sans-serif', size: 12, color: C.muted },
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
  const ACOR = {
    CN: C.verde, CH: C.dourado, LC: C.azulC, MT: C.critico, RED: C.roxo,
  };
  ED.Config = { C, BL, CFG, CFG_INTERACTIVE, AREAKEYS, AREANOME, ACOR };
})(window.EnemDash = window.EnemDash || {});
