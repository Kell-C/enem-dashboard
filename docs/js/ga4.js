(function (ED) {
  const TAB_LABELS = {
    'tab-ranking': 'Ranking das escolas',
    'tab-panorama': 'Indicadores',
    'tab-territorio': 'Território',
    'tab-distribuicao': 'Distribuição',
    'tab-redes': 'Redes',
    'tab-consistencia': 'Consistência',
    'tab-integridade': 'Integridade',
  };

  let enabled = false;
  let measurementId = null;
  let listenersBound = false;

  function readMeasurementId() {
    const meta = document.querySelector('meta[name="enem-ga4-id"]');
    const fromMeta = meta?.getAttribute('content')?.trim();
    if (fromMeta && /^G-[A-Z0-9]+$/i.test(fromMeta)) return fromMeta;
    const fromConfig = ED.Config?.GA4_MEASUREMENT_ID?.trim();
    if (fromConfig && /^G-[A-Z0-9]+$/i.test(fromConfig)) return fromConfig;
    return null;
  }

  function isLocalHost() {
    return ['localhost', '127.0.0.1'].includes(window.location.hostname);
  }

  function sanitizeParams(props) {
    const out = {};
    if (!props || typeof props !== 'object') return out;
    Object.keys(props).slice(0, 20).forEach((key) => {
      const val = props[key];
      if (val == null) return;
      if (typeof val === 'string') out[key] = val.slice(0, 120);
      else if (typeof val === 'number' || typeof val === 'boolean') out[key] = val;
    });
    return out;
  }

  function track(event, props) {
    if (!enabled || typeof window.gtag !== 'function') return;
    window.gtag('event', event, sanitizeParams(props));
  }

  function bindGlobalListeners() {
    if (listenersBound) return;
    listenersBound = true;

    document.addEventListener('dash-tab-show', (e) => {
      const tab = e.detail?.id;
      if (!tab) return;
      track('tab_view', {
        tab_id: tab,
        tab_name: TAB_LABELS[tab] || tab,
      });
    });

    document.addEventListener('enemdash:schoolZeroMode', (e) => {
      track('filter_change', {
        filter_name: 'notas_zero',
        filter_value: e.detail?.mode || 'all',
      });
    });

    let searchTimer = null;
    document.addEventListener('input', (ev) => {
      const el = ev.target;
      if (!(el instanceof HTMLInputElement) || el.type !== 'search') return;
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        const len = (el.value || '').trim().length;
        if (len > 0) {
          track('search', {
            query_length: len,
            search_context: el.id || 'search',
          });
        }
      }, 700);
    }, true);

    document.addEventListener('change', (ev) => {
      const el = ev.target;
      if (!(el instanceof HTMLSelectElement)) return;
      if (el.matches('[data-school-zero-mode]')) return;
      track('filter_change', {
        filter_name: el.id || el.name || 'select',
        filter_value: el.value,
      });
    }, true);
  }

  function activate(meta) {
    measurementId = readMeasurementId();
    if (!measurementId) return;

    const skipLocal = ED.Config?.GA4_SKIP_LOCALHOST !== false;
    if (skipLocal && isLocalHost()) return;

    if (!window.location.protocol.startsWith('http')) return;
    if (typeof window.gtag !== 'function') return;

    enabled = true;
    bindGlobalListeners();

    if (meta?.gerado_em) {
      track('dashboard_ready', {
        data_version: meta.gerado_em,
      });
    }
  }

  ED.initGa4 = activate;

  ED.track = track;
  ED.ga4Enabled = function () { return enabled; };
  ED.ga4MeasurementId = function () { return measurementId; };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => activate());
  } else {
    activate();
  }
})(window.EnemDash = window.EnemDash || {});
