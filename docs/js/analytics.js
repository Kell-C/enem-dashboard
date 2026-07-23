(function (ED) {
  const ENDPOINT = '/api/analytics/collect';
  const VISITOR_KEY = 'enemdash_vid';
  const RETURNING_KEY = 'enemdash_seen';
  const QUEUE_KEY = 'enemdash_aq';
  const FLUSH_MS = 4000;
  const MAX_QUEUE = 40;

  let sessionId = null;
  let visitorId = null;
  let queue = [];
  let flushTimer = null;
  let sessionStart = Date.now();
  let enabled = window.location.protocol.startsWith('http');

  function storageGet(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }

  function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch (_) { /* ignore */ }
  }

  function uuid() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function detectBrowser() {
    const ua = navigator.userAgent || '';
    if (ua.includes('Edg/')) return 'Edge';
    if (ua.includes('Chrome/')) return 'Chrome';
    if (ua.includes('Firefox/')) return 'Firefox';
    if (ua.includes('Safari/') && !ua.includes('Chrome/')) return 'Safari';
    return 'Outro';
  }

  function detectDevice() {
    const ua = (navigator.userAgent || '').toLowerCase();
    if (/ipad|tablet|kindle/.test(ua)) return 'tablet';
    if (/mobile|iphone|android/.test(ua)) return 'mobile';
    return 'desktop';
  }

  function normalizeReferrer() {
    const ref = document.referrer || '';
    if (!ref) return 'direto';
    try {
      const host = new URL(ref).hostname.replace(/^www\./, '');
      if (host === window.location.hostname.replace(/^www\./, '')) return 'mesmo site';
      return host;
    } catch (_) {
      return 'desconhecido';
    }
  }

  function basePayload() {
    return {
      session_id: sessionId,
      visitor_id: visitorId,
      device: detectDevice(),
      browser: detectBrowser(),
      referrer: normalizeReferrer(),
      is_returning: storageGet(RETURNING_KEY) === '1',
      ts: new Date().toISOString(),
    };
  }

  function persistQueue() {
    try {
      localStorage.setItem(QUEUE_KEY, JSON.stringify(queue.slice(-MAX_QUEUE)));
    } catch (_) { /* ignore */ }
  }

  function restoreQueue() {
    try {
      const raw = localStorage.getItem(QUEUE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) queue = parsed;
    } catch (_) { /* ignore */ }
  }

  function scheduleFlush() {
    if (flushTimer) return;
    flushTimer = window.setTimeout(() => {
      flushTimer = null;
      flush();
    }, FLUSH_MS);
  }

  function flush() {
    if (!enabled || !queue.length) return;
    const batch = queue.splice(0, MAX_QUEUE);
    persistQueue();

    const body = JSON.stringify({ events: batch });
    const blob = new Blob([body], { type: 'application/json' });

    if (navigator.sendBeacon && navigator.sendBeacon(ENDPOINT, blob)) {
      return;
    }

    fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {
      queue = batch.concat(queue).slice(-MAX_QUEUE);
      persistQueue();
    });
  }

  function track(event, props) {
    if (!enabled || !sessionId) return;
    const item = {
      ...basePayload(),
      event,
      props: props || {},
    };
    queue.push(item);
    if (queue.length >= 8) flush();
    else scheduleFlush();
  }

  function initIdentity() {
    visitorId = storageGet(VISITOR_KEY);
    if (!visitorId) {
      visitorId = uuid();
      storageSet(VISITOR_KEY, visitorId);
    }
    sessionId = uuid();
    storageSet(RETURNING_KEY, '1');
  }

  function bindGlobalListeners() {
    document.addEventListener('dash-tab-show', (e) => {
      const tab = e.detail?.id;
      if (!tab || tab === 'tab-analytics') return;
      track('tab_view', { tab });
    });

    document.addEventListener('enemdash:schoolZeroMode', (e) => {
      track('filter_change', { filter: 'notas_zero', value: e.detail?.mode || 'all' });
    });

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        track('session_end', { duration_sec: Math.round((Date.now() - sessionStart) / 1000) });
        flush();
      }
    });

    window.addEventListener('pagehide', () => {
      track('session_end', { duration_sec: Math.round((Date.now() - sessionStart) / 1000) });
      flush();
    });

    let searchTimer = null;
    document.addEventListener('input', (ev) => {
      const el = ev.target;
      if (!(el instanceof HTMLInputElement) || el.type !== 'search') return;
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        const len = (el.value || '').trim().length;
        if (len > 0) track('search', { query_length: len, context: el.id || 'search' });
      }, 700);
    }, true);

    document.addEventListener('change', (ev) => {
      const el = ev.target;
      if (!(el instanceof HTMLSelectElement)) return;
      if (el.matches('[data-school-zero-mode]')) return;
      track('filter_change', { filter: el.id || el.name || 'select', value: el.value });
    }, true);
  }

  function trackPageView(meta) {
    track('page_view', {
      path: window.location.pathname,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      language: navigator.language || '—',
      data_version: meta?.gerado_em || null,
      anos: meta?.anos || null,
    });
  }

  ED.initAnalytics = function (meta) {
    if (!enabled) return;
    initIdentity();
    restoreQueue();
    bindGlobalListeners();
    trackPageView(meta);
    scheduleFlush();
  };

  ED.track = track;
  ED.analyticsEnabled = function () { return enabled; };

  ED.checkAnalyticsApi = function () {
    if (!enabled) {
      return Promise.resolve({ ok: false, reason: 'protocolo' });
    }
    return fetch('/api/analytics/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('offline'))))
      .then((data) => ({ ok: true, data }))
      .catch(() => ({ ok: false, reason: 'servidor' }));
  };
})(window.EnemDash = window.EnemDash || {});
