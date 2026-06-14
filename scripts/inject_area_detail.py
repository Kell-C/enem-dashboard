#!/usr/bin/env python3
"""Injeta areaDetail em painel_data.js a partir de boxplot + histograma (+ integridade RED)."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "docs" / "data" / "painel_data.js"
ANOS = list(range(2019, 2025))
BIN_MID = [100, 300, 450, 550, 700, 900]
POS_LO = [1, 200, 400, 500, 600, 800]
POS_LABELS = ['1\u2013200', '200\u2013400', '400\u2013500', '500\u2013600', '600\u2013800', '800\u20131000']
BIN_LO = [1, 200, 400, 500, 600, 800]


def _load_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    payload = text.split("=", 1)[1].strip().rstrip(";")
    payload = payload.replace("null", "None").replace("true", "True").replace("false", "False")
    return eval(payload)


def _counts_from_pct(n: int, pct: list[float]) -> list[int]:
    if not n:
        return [0] * len(pct)
    raw = [n * p / 100.0 for p in pct]
    counts = [int(round(x)) for x in raw]
    diff = n - sum(counts)
    if diff != 0:
        order = sorted(range(len(pct)), key=lambda i: raw[i] - counts[i], reverse=(diff > 0))
        step = 1 if diff > 0 else -1
        for k in range(abs(diff)):
            counts[order[k % len(order)]] += step
    return counts


def _hist_counts_ms(n: int, ms: list[float], mn, pct_sem: float) -> tuple[list[int], list[float]]:
    """Contagens coerentes: 6 faixas legado -> 8 faixas (sem nota, zero, 1-200...)."""
    if not n:
        return [0] * 8, [0.0] * 8
    base = _counts_from_pct(n, ms)
    c_sem = round(n * pct_sem / 100) if pct_sem else 0
    if mn == 0:
        c_zero = max(1, base[0]) if base[0] > 0 else 1
        c_1_200 = max(0, base[0] - c_zero)
    else:
        c_zero = 0
        c_1_200 = base[0]
    counts = [c_sem, c_zero, c_1_200, base[1], base[2], base[3], base[4], base[5]]
    diff = n - sum(counts)
    if diff:
        order = sorted(range(2, 8), key=lambda i: counts[i], reverse=True)
        step = 1 if diff > 0 else -1
        for k in range(abs(diff)):
            counts[order[k % len(order)]] += step
    pct = [round(100 * c / n, 1) for c in counts]
    return counts, pct


def _min_pos_est(mn, ms_bins: list[float]) -> tuple[float | None, bool]:
    if mn is not None and mn > 0:
        return round(float(mn), 1), True
    if mn == 0:
        if ms_bins[0] > 0:
            return 1.0, False
        for j in range(1, len(ms_bins)):
            if ms_bins[j] > 0:
                return float(BIN_LO[j]), False
    return None, False


def _br_hist_pct(hist6: list[float], n_br: int | None) -> list[float]:
    """Aproxima faixas 8-bin para Brasil a partir do histograma legado (0-200 inclui zero)."""
    pct_sem = 0.0
    pct_zero = 0.0
    pos = list(hist6)
    if pos and pos[0] > 0:
        pos[0] = max(0.0, pos[0])
    return [pct_sem, pct_zero, max(0.0, pos[0]), pos[1], pos[2], pos[3], pos[4], pos[5]]


def _build_area_detail(data: dict) -> dict:
    box = data.get("boxplot", {})
    hist = data.get("histograma", {})
    integ = data.get("integ", {}).get("rede", {}).get("Estadual", {})
    tx_sem = integ.get("txS", [])
    filt = integ.get("filt", [])
    estadual_n = data.get("estadualN", [])
    out = {}
    for area in ["CN", "CH", "LC", "MT", "RED"]:
        out[area] = {}
        for i, ano in enumerate(ANOS):
            key = str(ano)
            bp = (box.get(area) or {}).get(key) or {}
            h = (hist.get(area) or {}).get(key) or {}
            ms = list(h.get("ms") or [0.0] * 6)
            br = list(h.get("br") or [0.0] * 6)
            while len(ms) < 6:
                ms.append(0.0)
            while len(br) < 6:
                br.append(0.0)

            n = int(filt[i]) if i < len(filt) and filt[i] else (
                int(estadual_n[i]) if i < len(estadual_n) and estadual_n[i] else None
            )
            pct_sem = float(tx_sem[i]) if area == "RED" and i < len(tx_sem) and tx_sem[i] is not None else 0.0
            mn = bp.get("min")

            c_zero = 0
            if mn == 0 and n:
                c_zero = 1
            pct_zero = round(100 * c_zero / n, 1) if n else 0.0

            hist_counts, hist_pct = _hist_counts_ms(n or 0, ms, mn, pct_sem)
            if not n:
                hist_pct = [pct_sem, pct_zero, *ms]

            pos_bins = hist_pct[2:]
            peak = max(range(6), key=lambda j: pos_bins[j])
            moda_faixa = POS_LABELS[peak] if pos_bins[peak] > 0 else None
            moda = round(float(BIN_MID[peak]), 1) if pos_bins[peak] > 0 else None

            min_pos, min_exact = _min_pos_est(mn, ms)
            br_pct6 = br[:]
            br_counts_base = _counts_from_pct(n or 0, br_pct6) if n else [0] * 6
            br_pct = [0.0, 0.0, *[round(100 * c / n, 1) if n else 0 for c in br_counts_base]]
            br_counts = [0, 0, *br_counts_base]

            out[area][key] = {
                "n": n,
                "pctSemNota": hist_pct[0],
                "pctZero": hist_pct[1],
                "moda": moda,
                "modaFaixa": moda_faixa,
                "modaTipo": "faixa",
                "minPos": min_pos,
                "minPosExact": min_exact,
                "histPct": hist_pct,
                "histCounts": hist_counts,
                "brHistPct": br_pct,
                "brHistCounts": br_counts,
            }
    return out


def main() -> None:
    data = _load_js(JS)
    data["areaDetail"] = _build_area_detail(data)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    JS.write_text(f"window.PAINEL_DATA={body};\n", encoding="utf-8")
    print("areaDetail injetado em", JS)


if __name__ == "__main__":
    main()
