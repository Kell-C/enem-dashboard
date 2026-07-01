"""Extrai codigos INEP do PDF de escolas estaduais MS."""
import re
import sys
from pathlib import Path

import pdfplumber

PDF = Path(r"C:\Users\User\Downloads\Contatos e Endereços das Escolas_Estaduais_Fev_2025 com códigos inep.pdf")

def extrair_ineps(pdf_path: Path) -> list[int]:
    text_parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts)
    # INEP MS: 8 digitos comecando com 50
    ineps = sorted({int(m) for m in re.findall(r"\b(50\d{6})\b", text)})
    return ineps, text

if __name__ == "__main__":
    ineps, text = extrair_ineps(PDF)
    print("total_ineps", len(ineps))
    print("primeiros", ineps[:10])
    print("ultimos", ineps[-5:])
    # salvar lista
    out = Path(__file__).resolve().parents[1] / "dados" / "aio" / "ineps_pdf_estaduais.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(str(i) for i in ineps), encoding="utf-8")
    print("salvo", out)
