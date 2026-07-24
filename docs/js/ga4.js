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

  const STORAGE_OWNER = 'enem-dash-traffic-class';
  const STORAGE_CURSOR = 'enem-dash-traffic-cursor';
  const BOT_UA = /bot|crawl|spider|slurp|bingpreview|facebookexternalhit|embedly|quora link preview|monitoring|headless|lighthouse|preview|wget|curl|python-requests|go-http-client|libwww|scrapy|phantomjs|selenium|puppeteer|playwright/i;

  let enabled = false;
  let measurementId = null;
  let listenersBound = false;
  let trafficCtx = null;

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

  function readQueryOverride() {
    try {
      const params = new URLSearchParams(window.location.search);
      const raw = (params.get('traffic') || params.get('enem_traffic') || '').trim().toLowerCase();
      if (!raw) return null;
      if (raw === 'owner' || raw === 'internal' || raw === 'dev' || raw === 'minha') return 'owner';
      if (raw === 'cursor' || raw === 'agent' || raw === 'cloud') return 'cursor';
      if (raw === 'bot' || raw === 'crawler') return 'bot';
      if (raw === 'external' || raw === 'public') return 'external';
      return null;
    } catch (_e) {
      return null;
    }
  }

  function stripTrafficQuery() {
    try {
      const url = new URL(window.location.href);
      if (!url.searchParams.has('traffic') && !url.searchParams.has('enem_traffic')) return;
      url.searchParams.delete('traffic');
      url.searchParams.delete('enem_traffic');
      const next = url.pathname + url.search + url.hash;
      window.history.replaceState({}, '', next);
    } catch (_e) { /* ignore */ }
  }

  function persistOverride(trafficClass, reason) {
    if (trafficClass === 'owner') {
      try { localStorage.setItem(STORAGE_OWNER, 'owner'); } catch (_e) { /* ignore */ }
    }
    if (trafficClass === 'cursor') {
      try { sessionStorage.setItem(STORAGE_CURSOR, 'cursor'); } catch (_e) { /* ignore */ }
    }
    return { class: trafficClass, reason };
  }

  function classifyTraffic() {
    const override = readQueryOverride();
    if (override) {
      stripTrafficQuery();
      return persistOverride(override, 'query_override');
    }

    try {
      if (localStorage.getItem(STORAGE_OWNER) === 'owner') {
        return { class: 'owner', reason: 'owner_marker' };
      }
    } catch (_e) { /* ignore */ }

    try {
      if (sessionStorage.getItem(STORAGE_CURSOR) === 'cursor') {
        return { class: 'cursor', reason: 'cursor_marker' };
      }
    } catch (_e) { /* ignore */ }

    if (isLocalHost()) {
      return { class: 'owner', reason: 'localhost' };
    }

    const ua = navigator.userAgent || '';
    if (BOT_UA.test(ua)) {
      return { class: 'bot', reason: 'user_agent' };
    }

    const ref = document.referrer || '';
    if (/cursor\.com|cursor\.sh|cursor\.so/i.test(ref)) {
      return { class: 'cursor', reason: 'referrer_cursor' };
    }

    if (navigator.webdriver === true) {
      return { class: 'cursor', reason: 'webdriver' };
    }

    if (/HeadlessChrome/i.test(ua)) {
      return { class: 'cursor', reason: 'headless_chrome' };
    }

    return { class: 'external', reason: 'default' };
  }

  function shouldSend(trafficClass) {
    if (ED.Config?.GA4_ONLY_EXTERNAL === true) return trafficClass === 'external';
    if (trafficClass === 'bot' && ED.Config?.GA4_SKIP_BOTS === true) return false;
    return true;
  }

  function trafficPayload() {
    const ctx = trafficCtx || classifyTraffic();
    return {
      traffic_class: ctx.class,
      traffic_reason: ctx.reason,
    };
  }

  function applyTrafficToGtag() {
    if (!trafficCtx || typeof window.gtag !== 'function' || !measurementId) return;
    const payload = trafficPayload();
    window.gtag('set', 'user_properties', {
      traffic_class: payload.traffic_class,
      traffic_reason: payload.traffic_reason,
    });
    window.gtag('config', measurementId, payload);
  }

  function sendClassifiedPageView() {
    if (!enabled || !shouldSend(trafficCtx.class)) return;
    track('page_view', {
      page_title: document.title,
      page_location: window.location.href,
      page_path: window.location.pathname + window.location.search,
      send_classified_view: true,
    });
  }

  function sanitizeParams(props) {
    const out = {};
    if (!props || typeof props !== 'object') return out;
    Object.keys(props).slice(0, 24).forEach((key) => {
      const val = props[key];
      if (val == null) return;
      if (typeof val === 'string') out[key] = val.slice(0, 120);
      else if (typeof val === 'number' || typeof val === 'boolean') out[key] = val;
    });
    return out;
  }

  function track(event, props) {
    if (!enabled || typeof window.gtag !== 'function') return;
    if (!shouldSend(trafficCtx?.class)) return;
    window.gtag('event', event, sanitizeParams({
      ...props,
      ...trafficPayload(),
    }));
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

  let pendingMeta = null;
  let bootstrapped = false;

  function maybeDashboardReady() {
    const gerado = pendingMeta?.gerado_em;
    if (!gerado || maybeDashboardReady._sent) return;
    maybeDashboardReady._sent = true;
    track('dashboard_ready', { data_version: gerado });
  }

  function activate(meta) {
    if (meta) pendingMeta = meta;

    measurementId = readMeasurementId();
    if (!measurementId) return;

    if (!trafficCtx) {
      trafficCtx = classifyTraffic();
      window.__enemDashTraffic = trafficCtx;
    }

    const skipLocal = ED.Config?.GA4_SKIP_LOCALHOST !== false;
    if (skipLocal && isLocalHost()) return;

    if (!window.location.protocol.startsWith('http')) return;
    if (typeof window.gtag !== 'function') return;

    if (!bootstrapped) {
      bootstrapped = true;
      enabled = true;
      applyTrafficToGtag();
      bindGlobalListeners();
      sendClassifiedPageView();
      track('traffic_classified', {
        traffic_class: trafficCtx.class,
        traffic_reason: trafficCtx.reason,
      });
    }

    maybeDashboardReady();
  }

  ED.initGa4 = activate;

  ED.track = track;
  ED.ga4Enabled = function () { return enabled; };
  ED.ga4MeasurementId = function () { return measurementId; };
  ED.ga4TrafficClass = function () { return trafficCtx?.class || null; };
  ED.ga4MarkOwner = function () {
    try { localStorage.setItem(STORAGE_OWNER, 'owner'); } catch (_e) { /* ignore */ }
    trafficCtx = { class: 'owner', reason: 'manual_marker' };
    applyTrafficToGtag();
    track('traffic_classified', { traffic_class: 'owner', traffic_reason: 'manual_marker' });
  };
  ED.ga4ClearOwner = function () {
    try { localStorage.removeItem(STORAGE_OWNER); } catch (_e) { /* ignore */ }
    trafficCtx = classifyTraffic();
    applyTrafficToGtag();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => activate());
  } else {
    activate();
  }
})(window.EnemDash = window.EnemDash || {});
