"""Páginas `contexto_nacional` — painel ENEM v15 (fase 5d)."""

from __future__ import annotations

from app.v15.pages.contexto_nacional_body import render_contexto_nacional

def aba_contexto_nacional(tabelas, anos_sel):
    render_contexto_nacional(**locals())

