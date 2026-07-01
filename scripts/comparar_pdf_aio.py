"""Compara INEPs do PDF estadual com cobertura AIO."""
import csv
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_INEPS = ROOT / "dados" / "aio" / "ineps_pdf_estaduais.txt"
AIO_CACHE = ROOT / "dados" / "aio" / "escolas_ms_descobertas.json"
RESUMO = ROOT / "dados" / "aio" / "enem_escolas_resumo.csv"
BASE = "https://www.aio.com.br"


def tem_painel_publico(inep: int) -> bool:
    req = urllib.request.Request(
        f"{BASE}/enem-por-escola/escola/{inep}",
        headers={"User-Agent": "enem-dashboard/1.0", "Accept": "text/html"},
    )
    try:
        body = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
    except urllib.error.HTTPError:
        return False
    return "Painel de Desempenho" in body


def main() -> None:
    pdf = sorted(int(x) for x in PDF_INEPS.read_text(encoding="utf-8").splitlines() if x.strip())
    aio = set(map(int, json.loads(AIO_CACHE.read_text(encoding="utf-8"))))
    com_dados = set()
    if RESUMO.exists():
        for row in csv.DictReader(RESUMO.open(encoding="utf-8-sig")):
            if not row.get("ERRO"):
                com_dados.add(int(row["CO_INEP"]))

    fora_auto = [i for i in pdf if i not in aio]
    publico_fora = []
    for inep in fora_auto:
        if tem_painel_publico(inep):
            publico_fora.append(inep)

    relatorio = {
        "pdf_total": len(pdf),
        "no_autocomplete_aio": len(pdf) - len(fora_auto),
        "fora_autocomplete": len(fora_auto),
        "com_dados_publicos_resumo": len([i for i in pdf if i in com_dados]),
        "fora_autocomplete_com_painel_publico": len(publico_fora),
        "fora_autocomplete_sem_painel": len(fora_auto) - len(publico_fora),
        "fora_autocomplete_lista": fora_auto,
        "fora_autocomplete_com_painel": publico_fora,
    }
    out = ROOT / "dados" / "aio" / "cobertura_pdf_vs_aio.json"
    out.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: relatorio[k] for k in relatorio if k not in ("fora_autocomplete_lista", "fora_autocomplete_com_painel")}, indent=2))


if __name__ == "__main__":
    main()
