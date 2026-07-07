"""
Baixa microdados ENEM do INEP (download.inep.gov.br) e extrai CSV de participantes.

URL padrao:
  https://download.inep.gov.br/microdados/microdados_enem_{ano}.zip

Uso:
  python fetch_microdados_inep.py --anos 2016 2017 2018
  python fetch_microdados_inep.py --anos 2018 --force
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from enem_config import PASTA_BRUTOS, configure_logging

logger = configure_logging(__name__)

INEP_URL = "https://download.inep.gov.br/microdados/microdados_enem_{ano}.zip"
CSV_PATTERNS = (
    re.compile(r"^DADOS/MICRODADOS_ENEM_\d{4}\.csv$", re.I),
    re.compile(r"^DADOS/PARTICIPANTES_\d{4}\.csv$", re.I),
    re.compile(r"^DADOS/microdados_enem_\d{4}\.csv$", re.I),
)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Referer": "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem",
    }


def _csv_destino(ano: int, member_name: str) -> Path:
    nome = Path(member_name).name
    return PASTA_BRUTOS / str(ano) / "DADOS" / nome


def _member_e_participantes(zf: zipfile.ZipFile) -> str | None:
    for name in zf.namelist():
        norm = name.replace("\\", "/")
        if any(p.match(norm) for p in CSV_PATTERNS):
            return name
    # fallback: qualquer CSV em DADOS com PARTICIPANTES ou MICRODADOS no nome
    for name in zf.namelist():
        norm = name.replace("\\", "/").upper()
        if "/DADOS/" in norm and norm.endswith(".CSV"):
            if "PARTICIPANTES" in norm or "MICRODADOS_ENEM" in norm:
                return name
    return None


def _baixar(url: str, destino: Path, force: bool = False, tentativas: int = 5) -> None:
    if destino.exists() and not force:
        logger.info("[cache] zip %s (%s MB)", destino, destino.stat().st_size // (1024 * 1024))
        return

    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".zip.part")
    req = urllib.request.Request(url, headers=_headers(), method="GET")

    for tentativa in range(1, tentativas + 1):
        logger.info("[download] %s -> %s (tentativa %s/%s)", url, destino, tentativa, tentativas)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                baixado = 0
                t0 = time.time()
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        baixado += len(chunk)
                        if total and baixado % (50 * 1024 * 1024) < len(chunk):
                            pct = 100 * baixado / total
                            mb = baixado // (1024 * 1024)
                            logger.info("  ... %s MB (%.1f%%)", mb, pct)

            if total and baixado < total * 0.95:
                raise RuntimeError(f"download incompleto: {baixado}/{total} bytes")

            tmp.replace(destino)
            logger.info("[ok] zip %s MB em %.0fs", destino.stat().st_size // (1024 * 1024), time.time() - t0)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError) as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if tentativa >= tentativas:
                raise
            espera = min(60, 5 * tentativa)
            logger.warning("[retry] falha no download (%s); aguardando %ss...", exc, espera)
            time.sleep(espera)


def extrair_participantes(ano: int, zip_path: Path, force: bool = False) -> Path | None:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        member = _member_e_participantes(zf)
        if member is None:
            logger.error("CSV participantes nao encontrado em %s", zip_path)
            logger.info("Membros: %s", zf.namelist()[:20])
            return None

        dest = _csv_destino(ano, member)
        if dest.exists() and not force and dest.stat().st_size > 1_000_000:
            logger.info("[cache] csv %s (%s MB)", dest, dest.stat().st_size // (1024 * 1024))
            return dest

        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("[extract] %s -> %s", member, dest)
        with zf.open(member) as src, open(dest, "wb") as out:
            while True:
                chunk = src.read(8 * 1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

    logger.info("[ok] csv %s MB", dest.stat().st_size // (1024 * 1024))
    # Libera espaco: o zip nao e necessario apos extracao bem-sucedida.
    if zip_path.exists() and dest.stat().st_size > 1_000_000:
        zip_mb = zip_path.stat().st_size // (1024 * 1024)
        zip_path.unlink()
        logger.info("[cleanup] zip removido (%s MB liberados)", zip_mb)
    return dest


def fetch_ano(ano: int, force: bool = False) -> Path | None:
    pasta = PASTA_BRUTOS / str(ano)
    zip_path = pasta / f"microdados_enem_{ano}.zip"
    url = INEP_URL.format(ano=ano)

    # CSV ja extraido?
    for nome in (
        f"MICRODADOS_ENEM_{ano}.csv",
        f"PARTICIPANTES_{ano}.csv",
        f"microdados_enem_{ano}.csv",
    ):
        candidato = pasta / "DADOS" / nome
        if candidato.exists() and not force and candidato.stat().st_size > 1_000_000:
            logger.info("[cache] %s", candidato)
            return candidato

    try:
        _baixar(url, zip_path, force=force)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"INEP HTTP {exc.code} ano {ano}: {url}") from exc

    return extrair_participantes(ano, zip_path, force=force)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baixa microdados ENEM do INEP")
    p.add_argument("--anos", type=int, nargs="+", default=[2016, 2017, 2018])
    p.add_argument("--force", action="store_true", help="Re-baixa e re-extrai mesmo com cache")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    ok: list[int] = []
    for ano in args.anos:
        logger.info("=" * 60)
        logger.info("INEP %s", ano)
        path = fetch_ano(ano, force=args.force)
        if path:
            ok.append(ano)
            logger.info("[ok] %s pronto: %s", ano, path)
        else:
            logger.error("[fail] %s", ano)

    if not ok:
        raise SystemExit("Nenhum ano baixado.")

    logger.info("Proximo passo: python processar_enem.py --anos %s", " ".join(str(a) for a in ok))


if __name__ == "__main__":
    main()
