"""Páginas `metodologia` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.metodologia_body import render_metodologia_detalhe, render_aba_metodologia

def _render_metodologia_detalhe() -> None:
    render_metodologia_detalhe(**locals())

def aba_metodologia():
    render_aba_metodologia(**locals())

