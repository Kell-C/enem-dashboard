#!/usr/bin/env python3
"""Restaura dados de 2025 no painel após regeneração sem parquet completo.

Uso: python scripts/restaurar_painel_2025.py [rev_git_antes_da_regeneracao]
Padrão: commit imediatamente anterior ao merge que apagou 2025 (0c65aa4).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "docs" / "data"
REF_DEFAULT = "0c65aa4"
IDX_2025 = 6
POR_AREA_KEYS = (
    "notaPorArea",
    "nPorArea",
    "txPorArea",
    "notaPorAreaSemZero",
    "nPorAreaSemZero",
    "txPorAreaSemZero",
)


def _load_git_json(rev: str, path: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{rev}:{path}"], text=True)
    if path.endswith(".js"):
        raw = raw.replace("window.PAINEL_DATA=", "").rstrip(";")
    return json.loads(raw)


def _load_file_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("window.PAINEL_DATA="):
        raw = raw.replace("window.PAINEL_DATA=", "").rstrip(";")
    return json.loads(raw)


def _write_outputs(painel: dict) -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    json_path = WEB / "data.json"
    js_path = WEB / "painel_data.js"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(painel, f, ensure_ascii=False, separators=(",", ":"))
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.PAINEL_DATA=")
        json.dump(painel, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";")


def _merge_dispersao(old_rows: list, new_rows: list) -> list:
    new_by_key = {(r.get("nome"), r.get("mun")): r for r in new_rows}
    out = []
    for row in old_rows:
        merged = dict(row)
        extra = new_by_key.get((row.get("nome"), row.get("mun")))
        if extra:
            for key in POR_AREA_KEYS:
                if key in extra:
                    merged[key] = extra[key]
        out.append(merged)
    return out


def restaurar(ref: str = REF_DEFAULT) -> dict:
    old = _load_git_json(ref, "docs/data/painel_data.js")
    new = _load_file_json(WEB / "painel_data.js")

    merged = json.loads(json.dumps(old))
    merged["escPorArea"] = new.get("escPorArea", {})

    for mun, schools in new.get("escHist", {}).items():
        if mun not in merged.get("escHist", {}):
            continue
        for sid, school in schools.items():
            if sid not in merged["escHist"][mun]:
                continue
            if school.get("porArea"):
                merged["escHist"][mun][sid]["porArea"] = school["porArea"]

    merged["dispersao"] = _merge_dispersao(
        merged.get("dispersao", []),
        new.get("dispersao", []),
    )

    meta = merged.setdefault("meta", {})
    meta["gerado_em"] = datetime.now().isoformat()
    meta["restauracao_2025"] = (
        f"Dados de 2025 restaurados de {ref} após regeneração parcial; "
        "escPorArea mantido da versão atual (por prova · snapshot 2024 até novo pipeline)."
    )
    return merged


def main() -> None:
    ref = sys.argv[1] if len(sys.argv) > 1 else REF_DEFAULT
    painel = restaurar(ref)
    _write_outputs(painel)
    print(f"Restaurado: medMs[2025]={painel['medMs'][IDX_2025]}")
    n2025 = sum(
        1
        for schools in painel.get("escHist", {}).values()
        for s in schools.values()
        if s.get("geral") and len(s["geral"]) > IDX_2025 and s["geral"][IDX_2025] is not None
    )
    print(f"Escolas com histórico 2025: {n2025}")
    print(f"escPorArea municípios: {len(painel.get('escPorArea', {}))}")
    print(f"Gravado em {WEB / 'painel_data.js'}")


if __name__ == "__main__":
    main()
