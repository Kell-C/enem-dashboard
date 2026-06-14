(function (ED) {
  ED.DataUtils = {
    formatNumber(n, precision = 1) {
      return n == null || Number.isNaN(n) ? '\u2014' : n.toFixed(precision).replace('.', ',');
    },
    formatInteger0(n) {
      return n == null || Number.isNaN(n) ? '\u2014' : Math.round(n).toString();
    },
    formatInteger(n) {
      return n == null ? '\u2014' : Number(n).toLocaleString('pt-BR');
    },
    calculateTrend(delta, isBetterLow = false) {
      if (delta == null || Number.isNaN(delta)) return { cls: 'trend', txt: '\u2014' };
      const threshold = 0.05;
      if (Math.abs(delta) < threshold) return { cls: 'trend up', txt: '\u25B2 est\u00e1vel' };
      const isUp = delta > 0;
      const isPositiveChange = isBetterLow ? !isUp : isUp;
      const fmt = ED.DataUtils.formatNumber(Math.abs(delta));
      return {
        cls: `trend ${isPositiveChange ? 'up' : 'down'}`,
        txt: `${isUp ? '\u25B2' : '\u25BC'} ${fmt}`,
      };
    },
    norm(s) {
      return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toUpperCase().replace(/[^A-Z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
    },
    hexToRgb(h) {
      const r = parseInt(h.slice(1, 3), 16);
      const g = parseInt(h.slice(3, 5), 16);
      const b = parseInt(h.slice(5, 7), 16);
      return `${r},${g},${b}`;
    },
  };
})(window.EnemDash);
