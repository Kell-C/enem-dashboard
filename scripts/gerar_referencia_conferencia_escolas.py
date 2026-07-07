"""Extrai referencia oficial (PDF Fev/2025) para conferencia no Google Sheets."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from enem_helpers import normalizar_texto  # noqa: E402

PDF_DEFAULT = Path(
    r"C:\Users\User\Downloads\Contatos e Endereços das Escolas_Estaduais_Fev_2025 com códigos inep.pdf"
)
CRES_XLSX = ROOT / "auxiliar" / "cres.xlsx"
OUT_JSON = ROOT / "scripts" / "google_apps_script" / "referencia_escolas.json"
OUT_GS = ROOT / "scripts" / "google_apps_script" / "ConferenciaEscolas.gs"
TEMPLATE_GS = ROOT / "scripts" / "google_apps_script" / "ConferenciaEscolas.template.gs"

SKIP_PREFIX = (
    "ESTADO DE",
    "SECRETARIA",
    "SUPERINTEND",
    "COORDENADORIA",
    "SETOR DE",
    "RELAÇÃO",
    "REDE ESTADUAL",
    "Página",
    "FONE:",
    "DIRETOR",
    "DIRETOR ADJ",
    "DIRETOR ADJNTO",
)
PAT_INEP = re.compile(r"^(50\d{6})\s+(.+)$")


def _carregar_cre_por_inep(cres_xlsx: Path) -> dict[str, str]:
    df = pd.read_excel(cres_xlsx, sheet_name="Cód.INEP-CREs")
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        raw = row.get("CÓD INEP")
        if pd.isna(raw):
            continue
        inep = str(int(float(raw))) if float(raw) == int(float(raw)) else str(raw).strip()
        if PAT_INEP.match(f"{inep} X"):
            out[inep] = str(row["CRE"]).strip()
    return out


def _municipios_ms(cres_xlsx: Path) -> set[str]:
    df = pd.read_excel(cres_xlsx, sheet_name="CREs")
    return {normalizar_texto(m) for m in df["MUNICÍPIO"].dropna()}


def _cre_por_municipio(cres_xlsx: Path) -> dict[str, str]:
    df = pd.read_excel(cres_xlsx, sheet_name="CREs")
    return {normalizar_texto(r["MUNICÍPIO"]): str(r["CRE"]).strip() for _, r in df.iterrows()}


def extrair_referencia_pdf(pdf_path: Path, cres_xlsx: Path) -> list[dict[str, str]]:
    muni_set = _municipios_ms(cres_xlsx)
    cre_inep = _carregar_cre_por_inep(cres_xlsx)
    cre_muni = _cre_por_municipio(cres_xlsx)

    with pdfplumber.open(pdf_path) as pdf:
        lines = [
            ln.strip()
            for page in pdf.pages
            for ln in (page.extract_text() or "").split("\n")
            if ln.strip()
        ]

    ref: list[dict[str, str]] = []
    municipio_atual = ""

    for line in lines:
        if any(line.upper().startswith(p.upper()) for p in SKIP_PREFIX):
            continue
        if line.upper() in {
            "URBANA",
            "RURAL",
            "MUNICÍPIO",
            "MUNICIPIO",
            "ESCOLA",
            "/",
            "DO INEP",
            "CÓDIGO",
            "CODIGO",
            "CÓDIDO",
        }:
            continue
        if line.upper().startswith(("CÓD", "COD")):
            continue

        m = PAT_INEP.match(line)
        if m:
            inep = m.group(1)
            mun = municipio_atual
            cre = cre_inep.get(inep) or cre_muni.get(normalizar_texto(mun), "")
            ref.append(
                {
                    "i": inep,
                    "e": m.group(2).strip(),
                    "m": mun,
                    "c": cre,
                }
            )
            continue

        if re.match(r"^\d{5}-\d{3}$", line):
            continue
        if "@" in line or re.match(r"^(R\.|AV\.|ROD\.|TRAVESSA|ESTR\.|FAZ\.|ALDEIA)", line, re.I):
            continue
        if normalizar_texto(line) in muni_set:
            municipio_atual = line

    return ref


def salvar_json(ref: list[dict[str, str]], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(ref, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def injetar_no_apps_script(ref: list[dict[str, str]], template: Path, dest: Path) -> None:
    if not template.exists():
        return
    payload = json.dumps(ref, ensure_ascii=False, separators=(",", ":"))
    # String JSON valida em JS (evita JSON.parse em array literal e apóstrofos quebrando sintaxe)
    js_string = json.dumps(payload)
    text = template.read_text(encoding="utf-8")
    text = text.replace("__REFERENCIA_JSON__", js_string)
    dest.write_text(text, encoding="utf-8")


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF_DEFAULT
    if not pdf.exists():
        raise SystemExit(f"PDF nao encontrado: {pdf}")
    if not CRES_XLSX.exists():
        raise SystemExit(f"Planilha CREs nao encontrada: {CRES_XLSX}")

    ref = extrair_referencia_pdf(pdf, CRES_XLSX)
    salvar_json(ref, OUT_JSON)
    injetar_no_apps_script(ref, TEMPLATE_GS, OUT_GS)

    print(f"Escolas extraidas do PDF: {len(ref)}")
    print(f"JSON: {OUT_JSON}")
    if OUT_GS.exists():
        print(f"Apps Script gerado: {OUT_GS}")


if __name__ == "__main__":
    main()
