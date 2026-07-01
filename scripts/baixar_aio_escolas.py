"""
Baixa histórico ENEM por escola (2013–2025) do site AIO Educação.

Usa códigos INEP (CO_ESCOLA) já presentes no painel / pipeline MS, consulta
https://www.aio.com.br/enem-por-escola/escola/{CO_INEP} e persiste médias por
área e metadados (rankings AIO quando disponíveis).

Metodologia AIO: média por prova entre quem concluiu aquela prova; mín. 10
participantes por edição (escolas abaixo disso retornam 404).

Uso:
    .venv/bin/python scripts/baixar_aio_escolas.py
    .venv/bin/python scripts/baixar_aio_escolas.py --limit 5
    .venv/bin/python scripts/baixar_aio_escolas.py --co-escola 50011413
    .venv/bin/python scripts/baixar_aio_escolas.py --delay 2.0 --resume
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import AREA_KEYS, PASTA_DADOS, WEB_DATA, configure_logging

logger = configure_logging(__name__)

AIO_ANOS = list(range(2013, 2026))
AIO_BASE = "https://www.aio.com.br/enem-por-escola/escola"
PASTA_AIO = PASTA_DADOS / "aio"
CACHE_DIR = PASTA_AIO / "cache"
PARQUET_OUT = PASTA_AIO / "historico_escolas.parquet"
JSON_OUT = PASTA_AIO / "historico_escolas.json"
META_OUT = PASTA_AIO / "meta_baixar_aio.json"

AIO_AREA_MAP = {
    "Linguagens": "LC",
    "Ciências Humanas": "CH",
    "Ciências da Natureza": "CN",
    "Matemática": "MT",
    "Redação": "RED",
}

USER_AGENT = (
    "Mozilla/5.0 (compatible; enem-dashboard-ms/1.0; +https://github.com/)"
)


def _co_escola_int(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def extrair_co_escolas_painel(path: Path | None = None) -> set[int]:
    path = path or (WEB_DATA / "painel_data.js")
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return {int(m) for m in re.findall(r'"id":"(\d+)"', text)}


def extrair_co_escolas_parquet() -> set[int]:
    ids: set[int] = set()
    candidatos = [
        PASTA_DADOS / "agregados" / "evolucao_escolas.parquet",
        PASTA_DADOS / "agregados" / "escolas_2024.parquet",
        PASTA_DADOS / f"enem_completo_2019_{2025}_.parquet",
    ]
    for ano in range(2024, 2026):
        candidatos.append(PASTA_DADOS / str(ano) / f"enem_resultados_{ano}_.parquet")

    for path in candidatos:
        if not path.exists():
            continue
        try:
            df = pd.read_parquet(path, columns=["CO_ESCOLA"])
        except Exception as exc:
            logger.debug("Ignorando %s: %s", path, exc)
            continue
        for v in df["CO_ESCOLA"].dropna().unique():
            co = _co_escola_int(v)
            if co:
                ids.add(co)
    return ids


def extrair_co_escolas_helpers() -> set[int]:
    ids: set[int] = set()
    try:
        from enem_helpers import carregar_concluintes_sed, carregar_cres

        _, conc_esc = carregar_concluintes_sed()
        if not conc_esc.empty and "CO_ESCOLA" in conc_esc.columns:
            for v in conc_esc["CO_ESCOLA"].dropna().unique():
                co = _co_escola_int(v)
                if co:
                    ids.add(co)

        cres = carregar_cres()
        if not cres.empty and "CO_ESCOLA" in cres.columns:
            for v in cres["CO_ESCOLA"].dropna().unique():
                co = _co_escola_int(v)
                if co:
                    ids.add(co)
    except Exception as exc:
        logger.debug("Fontes auxiliares indisponíveis: %s", exc)
    return ids


def listar_co_escolas_ms(extra: list[int] | None = None) -> list[int]:
    fontes: dict[str, set[int]] = {
        "painel_data.js": extrair_co_escolas_painel(),
        "parquet": extrair_co_escolas_parquet(),
        "helpers": extrair_co_escolas_helpers(),
    }
    if extra:
        fontes["cli"] = {int(x) for x in extra}

    todos: set[int] = set()
    for nome, ids in fontes.items():
        logger.info("CO_ESCOLA de %s: %s", nome, len(ids))
        todos |= ids

    # Códigos INEP de MS começam com 50
    ms = sorted(co for co in todos if 50_000_000 <= co < 51_000_000)
    logger.info("Total MS (50xxxxxxx): %s escolas", len(ms))
    return ms


def _fetch_url(url: str, timeout: float = 30.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body


def parse_aio_html(page: str, co_inep: int) -> dict | None:
    if "data-chart-data-value" not in page:
        return None

    m = re.search(r'data-chart-data-value="([^"]+)"', page)
    if not m:
        return None

    series = json.loads(html.unescape(m.group(1)))
    medias_por_ano: dict[int, dict[str, float]] = {}
    for s in series:
        area = AIO_AREA_MAP.get(s.get("name", ""))
        if not area:
            continue
        for pt in s.get("data", []):
            ano = int(pt["x"])
            y = pt.get("y")
            if y is None:
                continue
            medias_por_ano.setdefault(ano, {})[area] = float(y)

    if not medias_por_ano:
        return None

    nome = None
    for pat in (
        r'Painel de Desempenho:\s*<span class="text-primary">([^<]+)</span>',
        r'<span class="text-primary">([^<]+)</span>\s*</h2>',
    ):
        mm = re.search(pat, page, re.I | re.S)
        if mm:
            nome = html.unescape(mm.group(1)).strip()
            break

    municipio = None
    uf = None
    mm = re.search(r'>\s*([^<]+)\s*&mdash;\s*([A-Z]{2})\s*</span>', page)
    if mm:
        municipio = html.unescape(mm.group(1)).strip()
        uf = mm.group(2).strip()

    dependencia = None
    if "Estadual" in page:
        dep_m = re.search(r'>\s*Estadual\s*</span>', page)
        if dep_m:
            dependencia = "Estadual"
    if dependencia is None:
        for dep in ("Municipal", "Federal", "Privada"):
            if re.search(rf">\s*{dep}\s*</span>", page):
                dependencia = dep
                break

    rankings: dict[str, int | None] = {"mun": None, "ms": None, "br": None}
    rank_patterns = [
        (r"#(\d+)\s+em\s+[^<]+", "mun"),
        (r"#(\d+)\s+em\s+MS", "ms"),
        (r"#(\d+)\s+no\s+Brasil", "br"),
    ]
    for pat, key in rank_patterns:
        rm = re.search(pat, page, re.I)
        if rm:
            rankings[key] = int(rm.group(1))

    notas_2025: dict[str, float] = {}
    if 2025 in medias_por_ano:
        notas_2025 = medias_por_ano[2025]

    return {
        "CO_ESCOLA": co_inep,
        "NO_ESCOLA": nome,
        "NO_MUNICIPIO_ESC": municipio,
        "SG_UF_ESC": uf,
        "TP_DEPENDENCIA_ADM_ESC": dependencia,
        "rank_municipio_2025": rankings["mun"],
        "rank_ms_2025": rankings["ms"],
        "rank_brasil_2025": rankings["br"],
        "medias_por_ano": medias_por_ano,
        "notas_2025": notas_2025,
    }


def baixar_escola(
    co_inep: int,
    *,
    cache_dir: Path = CACHE_DIR,
    use_cache: bool = True,
) -> dict | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{co_inep}.html"

    if use_cache and cache_file.exists():
        page = cache_file.read_text(encoding="utf-8")
        parsed = parse_aio_html(page, co_inep)
        if parsed:
            return parsed

    url = f"{AIO_BASE}/{co_inep}"
    status, page = _fetch_url(url)
    if status == 404:
        logger.debug("CO_ESCOLA=%s: 404 (sem dados AIO)", co_inep)
        return None
    if status == 429:
        raise RuntimeError(f"Rate limit AIO (429) em {co_inep}")
    if status != 200:
        logger.warning("CO_ESCOLA=%s: HTTP %s", co_inep, status)
        return None

    cache_file.write_text(page, encoding="utf-8")
    return parse_aio_html(page, co_inep)


def registros_longos(parsed: dict) -> list[dict]:
    rows = []
    co = parsed["CO_ESCOLA"]
    base = {
        "CO_ESCOLA": co,
        "NO_ESCOLA": parsed.get("NO_ESCOLA"),
        "NO_MUNICIPIO_ESC": parsed.get("NO_MUNICIPIO_ESC"),
        "SG_UF_ESC": parsed.get("SG_UF_ESC"),
        "TP_DEPENDENCIA_ADM_ESC": parsed.get("TP_DEPENDENCIA_ADM_ESC"),
        "rank_municipio_2025": parsed.get("rank_municipio_2025"),
        "rank_ms_2025": parsed.get("rank_ms_2025"),
        "rank_brasil_2025": parsed.get("rank_brasil_2025"),
        "fonte": "AIO",
    }
    for ano, areas in sorted(parsed["medias_por_ano"].items()):
        vals = [areas.get(k) for k in AREA_KEYS if areas.get(k) is not None]
        media_geral = round(sum(vals) / len(vals), 2) if vals else None
        for area in AREA_KEYS:
            media = areas.get(area)
            if media is None:
                continue
            rows.append({
                **base,
                "NU_ANO": int(ano),
                "area": area,
                "media": round(float(media), 2),
                "media_geral": media_geral,
            })
    return rows


def _media_geral_snapshot(area_vals: dict) -> float | None:
    vals = [float(v) for v in area_vals.values() if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def consolidar_parquet(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros)
    return df.sort_values(["CO_ESCOLA", "NU_ANO", "area"]).reset_index(drop=True)


def executar(
    *,
    co_escolas: list[int] | None = None,
    limit: int | None = None,
    delay: float = 1.5,
    resume: bool = False,
    use_cache: bool = True,
) -> pd.DataFrame:
    PASTA_AIO.mkdir(parents=True, exist_ok=True)

    alvo = co_escolas or listar_co_escolas_ms()
    if limit:
        alvo = alvo[:limit]

    existentes: set[int] = set()
    if resume and PARQUET_OUT.exists():
        try:
            prev = pd.read_parquet(PARQUET_OUT, columns=["CO_ESCOLA"])
            existentes = set(prev["CO_ESCOLA"].astype(int).unique())
            logger.info("Retomando: %s escolas já no parquet", len(existentes))
        except Exception:
            pass

    todos_registros: list[dict] = []
    if resume and PARQUET_OUT.exists():
        try:
            prev_df = pd.read_parquet(PARQUET_OUT)
            todos_registros = prev_df.to_dict("records")
        except Exception:
            todos_registros = []

    ok = 0
    miss = 0
    erros = 0
    t0 = time.time()

    for i, co in enumerate(alvo, 1):
        if resume and co in existentes:
            continue
        logger.info("[%s/%s] CO_ESCOLA=%s", i, len(alvo), co)
        try:
            parsed = baixar_escola(co, use_cache=use_cache)
        except RuntimeError as exc:
            logger.error("%s — aguardando 60s", exc)
            time.sleep(60)
            try:
                parsed = baixar_escola(co, use_cache=use_cache)
            except Exception as exc2:
                logger.error("Falha definitiva %s: %s", co, exc2)
                erros += 1
                continue

        if parsed is None:
            miss += 1
        else:
            todos_registros.extend(registros_longos(parsed))
            ok += 1

        if i < len(alvo) and delay > 0:
            time.sleep(delay)

    df = consolidar_parquet(todos_registros)
    if not df.empty:
        df.to_parquet(PARQUET_OUT, index=False)
        # snapshot JSON (wide por escola) para inspeção
        snapshot = {}
        for co, grp in df.groupby("CO_ESCOLA"):
            esc = grp.iloc[0]
            areas = {a: [] for a in AREA_KEYS}
            geral = []
            for ano in AIO_ANOS:
                sub = grp[grp["NU_ANO"] == ano]
                area_vals = {}
                for _, r in sub.iterrows():
                    area_vals[r["area"]] = r["media"]
                for a in AREA_KEYS:
                    v = area_vals.get(a)
                    areas[a].append(float(v) if v is not None else None)
                geral.append(_media_geral_snapshot(area_vals))
            snapshot[str(int(co))] = {
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
        JSON_OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "escolas_consultadas": len(alvo),
        "com_dados": ok,
        "sem_dados": miss,
        "erros": erros,
        "duracao_s": round(time.time() - t0, 1),
        "parquet": str(PARQUET_OUT),
    }
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(
        "Concluído: %s com dados, %s sem dados, %s erros → %s (%s linhas)",
        ok, miss, erros, PARQUET_OUT, len(df),
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa histórico ENEM por escola do site AIO (MS).")
    parser.add_argument("--co-escola", type=int, action="append", dest="co_escolas", help="Código INEP específico (repita para vários)")
    parser.add_argument("--limit", type=int, help="Limita número de escolas")
    parser.add_argument("--delay", type=float, default=1.5, help="Segundos entre requisições (padrão 1.5)")
    parser.add_argument("--resume", action="store_true", help="Pula escolas já presentes no parquet")
    parser.add_argument("--no-cache", action="store_true", help="Ignora cache HTML local")
    parser.add_argument("--list-only", action="store_true", help="Só lista CO_ESCOLA encontrados")
    args = parser.parse_args()

    if args.list_only:
        ids = listar_co_escolas_ms(extra=args.co_escolas)
        for co in ids:
            print(co)
        print(f"# total: {len(ids)}", file=sys.stderr)
        return

    executar(
        co_escolas=args.co_escolas or None,
        limit=args.limit,
        delay=args.delay,
        resume=args.resume,
        use_cache=not args.no_cache,
    )


if __name__ == "__main__":
    main()
