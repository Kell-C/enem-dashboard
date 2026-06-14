(function (ED) {
  ED.createContext = function (data) {
    const DU = ED.DataUtils;
    const { C, BL, CFG, AREAKEYS, AREANOME, ACOR } = ED.Config;
    const DATA = data || {};
    const ANOS = DATA.anos || [2019, 2020, 2021, 2022, 2023, 2024];
    const MED_MS = DATA.medMs || [];
    const MED_BR = DATA.medBr || [];
    const TX_MS = DATA.txMs || [];
    const RANK_MS = DATA.rankMs || [];
    const GAP = MED_MS.map((v, i) =>
      v != null && MED_BR[i] != null ? +(v - MED_BR[i]).toFixed(1) : null
    );
    return {
      DATA, ANOS, MED_MS, MED_BR, TX_MS, RANK_MS, GAP,
      MS_AREA_2024: DATA.msArea2024 || {},
      MS_GERAL_2024: DATA.msGeral2024 ?? null,
      C, BL, CFG, AREAKEYS, AREANOME, ACOR,
      FMT: (n) => DU.formatNumber(n),
      FMT0: (n) => DU.formatInteger0(n),
      NF: (n) => DU.formatInteger(n),
      trendTag: (delta, inv) => DU.calculateTrend(delta, inv),
      norm: (s) => DU.norm(s),
    };
  };
})(window.EnemDash);
