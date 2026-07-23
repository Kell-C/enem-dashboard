#!/usr/bin/env python3
"""Servidor estático do painel ENEM com coleta de analítica de visitantes."""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ANALYTICS_DIR = ROOT / "dados" / "analytics"
EVENTS_FILE = ANALYTICS_DIR / "events.jsonl"
LOCK = threading.Lock()

TAB_LABELS = {
    "tab-ranking": "Ranking das escolas",
    "tab-panorama": "Indicadores",
    "tab-territorio": "Território",
    "tab-distribuicao": "Distribuição",
    "tab-redes": "Redes",
    "tab-consistencia": "Consistência",
    "tab-integridade": "Integridade",
    "tab-analytics": "Analítica",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def ensure_analytics_dir() -> None:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)


def append_events(events: list[dict[str, Any]]) -> None:
    ensure_analytics_dir()
    with LOCK, EVENTS_FILE.open("a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(days: int = 30) -> list[dict[str, Any]]:
    if not EVENTS_FILE.exists():
        return []
    cutoff = utc_now() - timedelta(days=days)
    out: list[dict[str, Any]] = []
    with LOCK, EVENTS_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = event.get("ts")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if dt >= cutoff:
                out.append(event)
    return out


def device_category(ua: str) -> str:
    ua_l = (ua or "").lower()
    if any(x in ua_l for x in ("ipad", "tablet", "kindle")):
        return "tablet"
    if any(x in ua_l for x in ("mobile", "iphone", "android")):
        return "mobile"
    return "desktop"


def summarize_events(events: list[dict[str, Any]], days: int) -> dict[str, Any]:
    page_views = [e for e in events if e.get("event") == "page_view"]
    sessions: dict[str, dict[str, Any]] = {}
    visitors = set()
    tab_counts: Counter[str] = Counter()
    school_counts: Counter[str] = Counter()
    cre_counts: Counter[str] = Counter()
    mun_counts: Counter[str] = Counter()
    device_counts: Counter[str] = Counter()
    browser_counts: Counter[str] = Counter()
    referrer_counts: Counter[str] = Counter()
    daily_visits: Counter[str] = Counter()
    hourly_visits: Counter[int] = Counter()
    search_lengths: list[int] = []
    filter_counts: Counter[str] = Counter()
    returning = 0
    new_visitors = 0

    for e in events:
        vid = e.get("visitor_id")
        sid = e.get("session_id")
        if vid:
            visitors.add(vid)
        if not sid:
            continue

        sess = sessions.setdefault(
            sid,
            {
                "session_id": sid,
                "visitor_id": vid,
                "started_at": e.get("ts"),
                "last_at": e.get("ts"),
                "page_views": 0,
                "events": 0,
                "tabs": set(),
                "duration_sec": 0,
                "device": e.get("device"),
                "browser": e.get("browser"),
                "referrer": e.get("referrer"),
                "is_returning": bool(e.get("is_returning")),
            },
        )
        sess["events"] += 1
        sess["last_at"] = e.get("ts")
        if e.get("device"):
            sess["device"] = e.get("device")
        if e.get("browser"):
            sess["browser"] = e.get("browser")

        name = e.get("event")
        props = e.get("props") or {}

        if name == "page_view":
            sess["page_views"] += 1
            day = (e.get("ts") or "")[:10]
            if day:
                daily_visits[day] += 1
            try:
                hour = datetime.fromisoformat((e.get("ts") or "").replace("Z", "+00:00")).hour
                hourly_visits[hour] += 1
            except ValueError:
                pass
            if e.get("device"):
                device_counts[e["device"]] += 1
            if e.get("browser"):
                browser_counts[e["browser"]] += 1
            ref = (e.get("referrer") or "direto").strip() or "direto"
            referrer_counts[ref] += 1
            if e.get("is_returning"):
                returning += 1
            else:
                new_visitors += 1

        if name == "tab_view":
            tab = props.get("tab") or "desconhecido"
            tab_counts[tab] += 1
            sess["tabs"].add(tab)

        if name == "school_view":
            label = props.get("municipio") or props.get("inep") or "escola"
            school_counts[label] += 1

        if name == "cre_select":
            cre_counts[props.get("cre") or "CRE"] += 1

        if name == "mun_select":
            mun_counts[props.get("municipio") or "município"] += 1

        if name == "search":
            if props.get("query_length") is not None:
                search_lengths.append(int(props["query_length"]))

        if name == "filter_change":
            key = f"{props.get('filter')}={props.get('value')}"
            filter_counts[key] += 1

        if name == "session_end" and props.get("duration_sec") is not None:
            sess["duration_sec"] = max(sess["duration_sec"], int(props["duration_sec"]))

    durations = [s["duration_sec"] for s in sessions.values() if s["duration_sec"] > 0]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
    bounce_sessions = sum(1 for s in sessions.values() if s["page_views"] <= 1 and len(s["tabs"]) <= 1)
    total_sessions = len(sessions) or 1

    recent_sessions = []
    for s in sorted(sessions.values(), key=lambda x: x["last_at"] or "", reverse=True)[:20]:
        recent_sessions.append(
            {
                "session_id": s["session_id"][:8] + "…",
                "visitor_id": (s["visitor_id"] or "")[:8] + "…",
                "started_at": s["started_at"],
                "last_at": s["last_at"],
                "duration_sec": s["duration_sec"],
                "device": s["device"] or "—",
                "browser": s["browser"] or "—",
                "tabs": len(s["tabs"]),
                "events": s["events"],
                "returning": s["is_returning"],
            }
        )

    def top(counter: Counter[str], n: int = 8) -> list[dict[str, Any]]:
        return [{"label": k, "count": v} for k, v in counter.most_common(n)]

    return {
        "generated_at": iso_now(),
        "period_days": days,
        "totals": {
            "events": len(events),
            "page_views": len(page_views),
            "unique_visitors": len(visitors),
            "sessions": len(sessions),
            "avg_duration_sec": avg_duration,
            "bounce_rate": round(100 * bounce_sessions / total_sessions, 1),
            "returning_visitors": returning,
            "new_visitors": new_visitors,
            "avg_search_length": round(sum(search_lengths) / len(search_lengths), 1) if search_lengths else 0,
        },
        "daily_visits": [
            {"date": d, "count": daily_visits[d]}
            for d in sorted(daily_visits)
        ],
        "hourly_visits": [
            {"hour": h, "count": hourly_visits[h]} for h in range(24) if hourly_visits[h]
        ],
        "tabs": [
            {
                "id": tid,
                "label": TAB_LABELS.get(tid, tid),
                "count": tab_counts[tid],
            }
            for tid, _ in tab_counts.most_common(8)
        ],
        "devices": top(device_counts),
        "browsers": top(browser_counts),
        "referrers": top(referrer_counts),
        "schools": top(school_counts),
        "cre": top(cre_counts),
        "municipios": top(mun_counts),
        "filters": top(filter_counts, 10),
        "recent_sessions": recent_sessions,
    }


class PainelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        if args and isinstance(args[0], str) and args[0].startswith("GET /api/analytics"):
            return
        super().log_message(fmt, *args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        if self.path.startswith("/api/analytics"):
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analytics/summary":
            qs = parse_qs(parsed.query)
            days = int(qs.get("days", ["30"])[0])
            days = max(1, min(days, 365))
            events = read_events(days)
            self._send_json(HTTPStatus.OK, summarize_events(events, days))
            return
        if parsed.path == "/api/analytics/health":
            self._send_json(HTTPStatus.OK, {"ok": True, "ts": iso_now()})
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/analytics/collect":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "json_invalido"})
            return

        batch = payload.get("events")
        if not isinstance(batch, list):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "events_obrigatorio"})
            return

        accepted = []
        for item in batch[:50]:
            if not isinstance(item, dict):
                continue
            event = {
                "id": str(uuid.uuid4()),
                "ts": item.get("ts") or iso_now(),
                "event": str(item.get("event") or "unknown")[:64],
                "session_id": str(item.get("session_id") or "")[:64],
                "visitor_id": str(item.get("visitor_id") or "")[:64],
                "device": str(item.get("device") or "")[:32],
                "browser": str(item.get("browser") or "")[:64],
                "referrer": str(item.get("referrer") or "")[:256],
                "is_returning": bool(item.get("is_returning")),
                "props": item.get("props") if isinstance(item.get("props"), dict) else {},
            }
            accepted.append(event)

        if accepted:
            append_events(accepted)

        self._send_json(HTTPStatus.OK, {"ok": True, "accepted": len(accepted)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor do painel ENEM com analítica")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    args = parser.parse_args()

    ensure_analytics_dir()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PainelHandler)
    print(f"Painel ENEM MS — http://127.0.0.1:{args.port}/index.html")
    print(f"Analítica: dados em {EVENTS_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
