"""
Detecta gaps no painel ENEM MS, baixa microdados faltantes do INEP,
regera agregados/web_data e executa revisao de consistencia.

Gaps tipicos:
  - 2013-2015: CSV individual INEP ausente -> integridade/eliminados zerados
  - Parquet consolidado sem 2013-2018 (opcional; cache INEP cobre agregados)

Uso:
  python completar_gaps_painel.py --dry-run
  python completar_gaps_painel.py
  python completar_gaps_painel.py --skip-download --limpar-csv-apos-cache
  python completar_gaps_painel.py --revisao-only
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enem_config import (
    ANOS,
    ANOS_ESCOLA_PAINEL,
    ANOS_MICRODADOS,
    ANOS_MICRO_HISTORICO,
    AREA_KEYS,
    PASTA_AGREGADOS,
    PASTA_BRUTOS,
    PASTA_DADOS,
    REDE_REFERENCIA,
    WEB_DATA,
    configure_logging,
    resolver_parquet,
)
from enem_inep_csv import ANOS_INEP_CSV, csv_disponivel, _cache_path
from fetch_microdados_inep import fetch_ano, extrair_participantes

logger = configure_logging(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent
AGREGADOS_OBRIGATORIOS = (
    "participacao_ano",
    "desempenho",
    "integridade",
    "quantis",
    "histograma",
    "sumario",
)


def _run_script(nome: str, *args: str) -> None:
    cmd = [sys.executable, str(SCRIPTS_DIR / nome), *args]
    logger.info("[exec] %s", " ".join(cmd))
    subprocess.run(cmd, cwd=str(SCRIPTS_DIR), check=True)


def _parquet_anos() -> list[int]:
    path = resolver_parquet()
    if not path.exists():
        return []
    df = pd.read_parquet(path, columns=["NU_ANO"])
    return sorted(pd.to_numeric(df["NU_ANO"], errors="coerce").dropna().astype(int).unique())


def _integridade_anos() -> list[int]:
    path = PASTA_AGREGADOS / "integridade.parquet"
    if not path.exists():
        return []
    df = pd.read_parquet(path)
    if "escopo" in df.columns:
        df = df[df["escopo"] == REDE_REFERENCIA]
    return sorted(df["ano"].dropna().astype(int).unique())


def _web_data_mtime() -> float | None:
    for nome in ("data.json", "painel_data.js"):
        p = WEB_DATA / nome
        if p.exists():
            return p.stat().st_mtime
    return None


def _agregados_mtime() -> float | None:
    mtimes = [
        (PASTA_AGREGADOS / f"{n}.parquet").stat().st_mtime
        for n in AGREGADOS_OBRIGATORIOS
        if (PASTA_AGREGADOS / f"{n}.parquet").exists()
    ]
    return max(mtimes) if mtimes else None


def _csv_tamanho_ok(ano: int, min_mb: int = 3000) -> bool:
    for nome in (f"MICRODADOS_ENEM_{ano}.csv", f"PARTICIPANTES_{ano}.csv"):
        path = PASTA_BRUTOS / str(ano) / "DADOS" / nome
        if path.exists() and path.stat().st_size >= min_mb * 1024 * 1024:
            return True
    return _cache_path(ano).exists()


def auditar_gaps() -> dict[str, Any]:
    csv_faltando = [a for a in ANOS_INEP_CSV if not csv_disponivel(a)]
    csv_corrompido = [
        a for a in ANOS_MICRO_HISTORICO
        if a not in csv_faltando and not _cache_path(a).exists() and not _csv_tamanho_ok(a)
    ]
    parquet_anos = set(_parquet_anos())
    integ_anos = set(_integridade_anos())

    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "timestamp": now,
        "csv_individual_faltando": csv_faltando,
        "csv_corrompido_ou_parcial": csv_corrompido,
        "parquet_path": str(resolver_parquet()),
        "parquet_anos": sorted(parquet_anos),
        "parquet_anos_faltando": [a for a in ANOS_MICRODADOS if a not in parquet_anos],
        "integridade_anos": sorted(integ_anos),
        "integridade_anos_faltando": [a for a in ANOS if a not in integ_anos],
        "agregados_faltando": [
            n for n in AGREGADOS_OBRIGATORIOS if not (PASTA_AGREGADOS / f"{n}.parquet").exists()
        ],
        "escola_historico_parquet": (PASTA_DADOS / "enem_escola_historico.parquet").exists(),
        "web_data_desatualizado": bool(_web_data_mtime() and _agregados_mtime() and _agregados_mtime() > _web_data_mtime()),
        "prioridade_download": sorted(set(csv_faltando) | set(csv_corrompido)),
    }


def imprimir_auditoria(gaps: dict[str, Any]) -> None:
    logger.info("=" * 60)
    logger.info("AUDITORIA DE GAPS")
    logger.info("=" * 60)
    logger.info("CSV individual faltando: %s", gaps["csv_individual_faltando"] or "nenhum")
    logger.info("CSV parcial/corrompido: %s", gaps["csv_corrompido_ou_parcial"] or "nenhum")
    logger.info("Parquet: %s | anos %s", gaps["parquet_path"], gaps["parquet_anos"])
    logger.info("Integridade: anos %s | faltando %s", gaps["integridade_anos"], gaps["integridade_anos_faltando"] or "nenhum")
    logger.info("Prioridade download: %s", gaps["prioridade_download"] or "nenhum")


def baixar_faltantes(anos: list[int], force: bool = False) -> list[int]:
    ok: list[int] = []
    for ano in anos:
        logger.info("-" * 40)
        zip_path = PASTA_BRUTOS / str(ano) / f"microdados_enem_{ano}.zip"
        if zip_path.exists() and not _csv_tamanho_ok(ano) and not force:
            logger.info("Re-extraindo %s a partir do zip local", ano)
            path = extrair_participantes(ano, zip_path, force=True)
            if path and _csv_tamanho_ok(ano):
                ok.append(ano)
                continue
        try:
            path = fetch_ano(ano, force=force)
            if path and _csv_tamanho_ok(ano):
                ok.append(ano)
                logger.info("[ok] %s -> %s", ano, path)
            else:
                logger.error("[fail] CSV incompleto ou ausente para %s", ano)
        except Exception as exc:
            logger.error("[fail] download %s: %s", ano, exc)
    return ok


def _limpar_csv_bruto(anos: list[int]) -> None:
    for ano in anos:
        if not _cache_path(ano).exists():
            continue
        for nome in (f"MICRODADOS_ENEM_{ano}.csv", f"PARTICIPANTES_{ano}.csv"):
            path = PASTA_BRUTOS / str(ano) / "DADOS" / nome
            if path.exists():
                mb = path.stat().st_size // (1024 * 1024)
                path.unlink()
                logger.info("[cleanup] CSV bruto removido: %s (%s MB)", path, mb)
        zip_path = PASTA_BRUTOS / str(ano) / f"microdados_enem_{ano}.zip"
        if zip_path.exists():
            mb = zip_path.stat().st_size // (1024 * 1024)
            zip_path.unlink()
            logger.info("[cleanup] zip removido: %s (%s MB)", zip_path, mb)


def processar_microdados(anos: list[int]) -> None:
    if anos:
        _run_script("processar_enem.py", "--anos", *[str(a) for a in sorted(anos)])


def regerar_painel() -> None:
    _run_script("gerar_agregados.py")
    _run_script("gerar_web_data.py")


def revisar_consistencia(gaps_antes: dict[str, Any] | None = None) -> dict[str, Any]:
    rel: dict[str, Any] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "ok": True,
        "checks": [],
        "warnings": [],
        "errors": [],
        "stats": {},
    }

    def check(nome: str, ok: bool, detalhe: str, nivel: str = "error") -> None:
        rel["checks"].append({"nome": nome, "ok": ok, "detalhe": detalhe})
        if ok:
            logger.info("[ok] %s: %s", nome, detalhe)
        elif nivel == "warning":
            rel["warnings"].append(f"{nome}: {detalhe}")
            logger.warning("[warn] %s: %s", nome, detalhe)
        else:
            rel["ok"] = False
            rel["errors"].append(f"{nome}: {detalhe}")
            logger.error("[erro] %s: %s", nome, detalhe)

    for nome in AGREGADOS_OBRIGATORIOS:
        path = PASTA_AGREGADOS / f"{nome}.parquet"
        check(f"agregado_{nome}", path.exists(), str(path) if path.exists() else "ausente")

    pa_path = PASTA_AGREGADOS / "participacao_ano.parquet"
    if pa_path.exists():
        pa = pd.read_parquet(pa_path)
        ms = pa[pa["dependencia"] == REDE_REFERENCIA].copy()
        anos_pa = sorted(ms["ano"].astype(int).unique())
        check("participacao_anos_completos", anos_pa == ANOS, f"anos={anos_pa}")
        rel["stats"]["participacao_ms"] = ms.assign(
            taxa=lambda d: (100 * d["presentes_filt"] / d["concluintes"]).where(d["concluintes"] > 0)
        )[["ano", "presentes_filt", "concluintes", "taxa"]].to_dict("records")

    int_path = PASTA_AGREGADOS / "integridade.parquet"
    if int_path.exists():
        ms_i = integ[integ["escopo"] == REDE_REFERENCIA] if (integ := pd.read_parquet(int_path)) is not None else pd.DataFrame()
        anos_i = sorted(ms_i["ano"].astype(int).unique())
        check("integridade_anos_completos", anos_i == ANOS, f"anos={anos_i}; faltando={sorted(set(ANOS)-set(anos_i))}")
        for _, row in ms_i.iterrows():
            ano = int(row["ano"])
            er, et, filt = int(row.get("elim_redacao", 0)), int(row.get("eliminados_total", 0)), int(row.get("filt", 0))
            if filt > 0 and et > filt:
                check(f"integridade_et_{ano}", False, f"eliminados_total ({et}) > filt ({filt})")
            if ano in ANOS_MICRO_HISTORICO and er == 0 and et == 0:
                check(f"integridade_historico_{ano}", False, "eliminados zerados", "warning")
        rel["stats"]["integridade_ms"] = ms_i[["ano", "filt", "eliminados_total", "elim_redacao", "tx_elim"]].to_dict("records")

    data_json = WEB_DATA / "data.json"
    if data_json.exists():
        web = json.loads(data_json.read_text(encoding="utf-8"))
        check("web_data_anos", web.get("anos") == ANOS, f"anos={web.get('anos')}")
        er = web.get("integ", {}).get("rede", {}).get(REDE_REFERENCIA, {}).get("er", [])
        zeros_hist = [(a, v) for a, v in zip(web.get("anos", ANOS), er) if a in ANOS_MICRO_HISTORICO and v == 0]
        check("web_integridade_historico", len(zeros_hist) == 0,
              f"redacao anulada zerada em {[a for a, _ in zeros_hist]}" if zeros_hist else "ok")

    rel["summary"] = {"status": "OK" if rel["ok"] else "COM ERROS", "errors": len(rel["errors"]), "warnings": len(rel["warnings"])}
    return rel


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime.datetime)):
        return obj.isoformat()
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(obj, float) and pd.isna(obj):
        return None
    return obj


def salvar_relatorio(gaps: dict[str, Any], revisao: dict[str, Any]) -> Path:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    out = WEB_DATA / "meta_revisao_dados.json"
    payload = _json_safe({"gaps": gaps, "revisao": revisao})
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[meta] revisao gravada: %s", out)
    return out


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Completa gaps do painel ENEM MS e revisa dados")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--skip-process", action="store_true")
    p.add_argument("--consolidar-parquet", action="store_true")
    p.add_argument("--limpar-csv-apos-cache", action="store_true")
    p.add_argument("--skip-agregados", action="store_true")
    p.add_argument("--revisao-only", action="store_true")
    p.add_argument("--force-download", action="store_true")
    p.add_argument("--anos", type=int, nargs="+")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    t0 = time.time()
    gaps = auditar_gaps()
    imprimir_auditoria(gaps)

    if args.revisao_only:
        revisao = revisar_consistencia(gaps)
        salvar_relatorio(gaps, revisao)
        if not revisao["ok"]:
            raise SystemExit(f"Revisao encontrou {len(revisao['errors'])} erro(s)")
        return
    if args.dry_run:
        return

    anos_download = args.anos or gaps["prioridade_download"]
    if not args.skip_download and anos_download:
        baixados = baixar_faltantes(anos_download, force=args.force_download)
        gaps = auditar_gaps()
        if not baixados and not any(csv_disponivel(a) for a in anos_download):
            raise SystemExit(f"Falha no download: {anos_download}")

    if args.consolidar_parquet and not args.skip_process:
        anos_processar = [a for a in (anos_download or []) if a <= 2018 and csv_disponivel(a)]
        if anos_processar:
            processar_microdados(anos_processar)

    if not args.skip_agregados:
        regerar_painel()

    if args.limpar_csv_apos_cache:
        _limpar_csv_bruto([a for a in ANOS_INEP_CSV if _cache_path(a).exists()])

    gaps_pos = auditar_gaps()
    revisao = revisar_consistencia(gaps_pos)
    salvar_relatorio(gaps_pos, revisao)
    logger.info("CONCLUIDO em %.1f min | %s", (time.time() - t0) / 60, revisao["summary"])
    if not revisao["ok"]:
        raise SystemExit(f"Revisao encontrou {len(revisao['errors'])} erro(s)")


if __name__ == "__main__":
    main()
