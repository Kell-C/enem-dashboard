(function (ED) {
  ED.createContext = function (data) {
    const DU = ED.DataUtils;
    const { C, BL, CFG, AREAKEYS, AREANOME, ACOR } = ED.Config;
    const DATA = data || {};
    const ANOS = DATA.anos || [2019, 2020, 2021, 2022, 2023, 2024, 2025];
    const LAST_INDEX = ANOS.length - 1;
    const LAST_YEAR = ANOS[LAST_INDEX];
    const PREV_YEAR = ANOS[Math.max(0, LAST_INDEX - 1)];
    const MED_MS = DATA.medMs || [];
    const MED_BR = DATA.medBr || [];
    const MED_MS_SEM_ZERO = DATA.medMsSemZero || [];
    const MED_BR_SEM_ZERO = DATA.medBrSemZero || [];
    const TX_MS = DATA.txMs || [];
    const TX_MS_SEM_ZERO = DATA.txMsSemZero || [];
    const RANK_MS = DATA.rankMs || [];
    const RANK_MS_SEM_ZERO = DATA.rankMsSemZero || [];
    const GAP = MED_MS.map((v, i) =>
      v != null && MED_BR[i] != null ? +(v - MED_BR[i]).toFixed(1) : null
    );
    ED.getSchoolZeroMode = function () {
      return ED.schoolZeroMode === 'no_zero' ? 'no_zero' : 'all';
    };
    ED.setSchoolZeroMode = function (mode) {
      ED.schoolZeroMode = mode === 'no_zero' ? 'no_zero' : 'all';
      document.querySelectorAll('[data-school-zero-mode]').forEach((el) => {
        if (el.value !== ED.schoolZeroMode) el.value = ED.schoolZeroMode;
      });
      document.dispatchEvent(new CustomEvent('enemdash:schoolZeroMode', {
        detail: { mode: ED.schoolZeroMode },
      }));
    };
    return {
      DATA, ANOS, LAST_INDEX, LAST_YEAR, PREV_YEAR, MED_MS, MED_BR, MED_MS_SEM_ZERO, MED_BR_SEM_ZERO,
      TX_MS, TX_MS_SEM_ZERO, RANK_MS, RANK_MS_SEM_ZERO, GAP,
      MS_AREA_2024: DATA.msArea2024 || {},
      MS_GERAL_2024: DATA.msGeral2024 ?? null,
      MS_AREA_2024_SEM_ZERO: DATA.msArea2024SemZero || {},
      MS_GERAL_2024_SEM_ZERO: DATA.msGeral2024SemZero ?? null,
      C, BL, CFG, AREAKEYS, AREANOME, ACOR,
      FMT: (n) => DU.formatNumber(n),
      FMT0: (n) => DU.formatInteger0(n),
      NF: (n) => DU.formatInteger(n),
      trendTag: (delta, inv) => DU.calculateTrend(delta, inv),
      norm: (s) => DU.norm(s),
    };
  };
})(window.EnemDash);
