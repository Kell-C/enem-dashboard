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

  function readMeasurementId() {
    const meta = document.querySelector('meta[name="enem-ga4-id"]');
    const fromMeta = meta?.getAttribute('content')?.trim();
    if (fromMeta && /^G-[A-Z0-9]+$/i.test(fromMeta)) return fromMeta;
    const fromConfig = ED.Config?.GA4_MEASUREMENT_ID?.trim();
    if (fromConfig && /^G-[A-Z0-9]+$/i.test(fromConfig)) return fromConfig;
    return null;
  }

  function isLocalHost() {
    return ['localhost', '127.0.0.1', ''].includes(window.location.hostname);
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

  function loadGtag(id) {
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag() { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, {
      send_page_view: false,
      cookie_flags: 'SameSite=None;Secure',
    });

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.appendChild(script);
  }

  function track(event, props) {
    if (!enabled || typeof window.gtag !== 'function') return;
    window.gtag('event', event, sanitizeParams(props));
  }

  function bindGlobalListeners() {
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

  ED.initGa4 = function (meta) {
    measurementId = readMeasurementId();
    if (!measurementId) return;

    const skipLocal = ED.Config?.GA4_SKIP_LOCALHOST !== false;
    if (skipLocal && isLocalHost()) return;

    if (!window.location.protocol.startsWith('http')) return;

    loadGtag(measurementId);
    enabled = true;
    bindGlobalListeners();

    track('page_view', {
      page_title: document.title,
      page_location: window.location.href,
      data_version: meta?.gerado_em || null,
    });
  };

  ED.track = track;
  ED.ga4Enabled = function () { return enabled; };
  ED.ga4MeasurementId = function () { return measurementId; };
})(window.EnemDash = window.EnemDash || {});
