"""
Exporta dados AIO (historico_escolas.parquet) para docs/data/aio_data.js.

Uso:
    .venv/bin/python scripts/gerar_aio_web_data.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import AREA_KEYS, PASTA_DADOS, WEB_DATA, configure_logging

logger = configure_logging(__name__)

AIO_ANOS = list(range(2013, 2026))
PASTA_AIO = PASTA_DADOS / "aio"
PARQUET_IN = PASTA_AIO / "historico_escolas.parquet"
JSON_IN = PASTA_AIO / "historico_escolas.json"


def _media_geral(row_areas: dict[str, float | None]) -> float | None:
    vals = [v for v in row_areas.values() if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def build_aio_data() -> dict:
    if JSON_IN.exists():
        escolas = json.loads(JSON_IN.read_text(encoding="utf-8"))
    elif PARQUET_IN.exists():
        df = pd.read_parquet(PARQUET_IN)
        escolas = {}
        for co, grp in df.groupby("CO_ESCOLA"):
            esc = grp.iloc[0]
            anos = sorted(int(a) for a in grp["NU_ANO"].unique())
            areas = {k: [] for k in AREA_KEYS}
            geral = []
            for ano in AIO_ANOS:
                sub = grp[grp["NU_ANO"] == ano]
                area_vals = {}
                for _, r in sub.iterrows():
                    area_vals[r["area"]] = float(r["media"])
                for k in AREA_KEYS:
                    areas[k].append(area_vals.get(k))
                geral.append(_media_geral(area_vals))
            escolas[str(int(co))] = {
                "id": str(int(co)),
                "nome": esc.get("NO_ESCOLA"),
                "mun": esc.get("NO_MUNICIPIO_ESC"),
                "dependencia": esc.get("TP_DEPENDENCIA_ADM_ESC"),
                "ranking2025": {
                    "mun": int(esc["rank_municipio_2025"]) if pd.notna(esc.get("rank_municipio_2025")) else None,
                    "ms": int(esc["rank_ms_2025"]) if pd.notna(esc.get("rank_ms_2025")) else None,
                    "br": int(esc["rank_brasil_2025"]) if pd.notna(esc.get("rank_brasil_2025")) else None,
                },
                "anos": AIO_ANOS,
                "areas": areas,
                "geral": geral,
            }
    else:
        logger.warning("Nenhum dado AIO em %s — rode baixar_aio_escolas.py", PASTA_AIO)
        return {
            "meta": {"vazio": True},
            "anos": AIO_ANOS,
            "escolas": {},
            "ranking2025": [],
        }

    # Enriquecer CRE a partir do painel, se disponível
    painel_path = WEB_DATA / "painel_data.js"
    cre_map: dict[str, str] = {}
    if painel_path.exists():
        text = painel_path.read_text(encoding="utf-8")
        import re
        for m in re.finditer(
            r'"id":"(\d+)"[^}]*?"nome":"([^"]+)"[^}]*?(?:"cre":"([^"]*)")?',
            text,
        ):
            if m.group(3):
                cre_map[m.group(1)] = m.group(3)

    ranking_rows = []
    for sid, esc in escolas.items():
        if cre_map.get(sid):
            esc["cre"] = cre_map[sid]
        idx_2025 = AIO_ANOS.index(2025) if 2025 in AIO_ANOS else None
        if idx_2025 is None:
            continue
        g = esc.get("geral", [])
        if not g or idx_2025 >= len(g) or g[idx_2025] is None:
            continue
        areas = esc.get("areas", {})
        row = {
            "id": sid,
            "nome": esc.get("nome") or sid,
            "mun": esc.get("mun"),
            "cre": esc.get("cre"),
            "dependencia": esc.get("dependencia") or "Estadual",
            "geral": g[idx_2025],
            "cn": areas.get("CN", [None] * len(AIO_ANOS))[idx_2025],
            "ch": areas.get("CH", [None] * len(AIO_ANOS))[idx_2025],
            "lc": areas.get("LC", [None] * len(AIO_ANOS))[idx_2025],
            "mt": areas.get("MT", [None] * len(AIO_ANOS))[idx_2025],
            "red": areas.get("RED", [None] * len(AIO_ANOS))[idx_2025],
            "rankMs": esc.get("ranking2025", {}).get("ms"),
            "rankMun": esc.get("ranking2025", {}).get("mun"),
            "rankBr": esc.get("ranking2025", {}).get("br"),
        }
        ranking_rows.append(row)

    # Ranking calculado entre escolas MS com dados 2025 (estaduais primeiro)
    ranking_rows.sort(key=lambda r: (-(r["geral"] or 0), r["nome"] or ""))
    for i, row in enumerate(ranking_rows, 1):
        row["rankCalc"] = i

    return {
        "meta": {
            "fonte": "AIO Educação (aio.com.br/enem-por-escola)",
            "metodologia": "Média por prova entre quem concluiu cada área; mín. 10 participantes/edição",
            "anos": AIO_ANOS,
            "gerado_em": datetime.datetime.now().isoformat(),
            "n_escolas": len(escolas),
        },
        "anos": AIO_ANOS,
        "escolas": escolas,
        "ranking2025": ranking_rows,
    }


def main() -> None:
    data = build_aio_data()
    out = WEB_DATA / "aio_data.js"
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    out.write_text(f"window.AIO_DATA={payload};\n", encoding="utf-8")
    meta_path = WEB_DATA / "meta_gerar_aio_web_data.json"
    meta_path.write_text(
        json.dumps(
            {
                "gerado_em": data["meta"].get("gerado_em"),
                "n_escolas": data["meta"].get("n_escolas", 0),
                "ranking2025": len(data.get("ranking2025", [])),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Exportado %s (%s escolas, ranking 2025: %s)", out, data["meta"].get("n_escolas", 0), len(data.get("ranking2025", [])))


if __name__ == "__main__":
    main()
