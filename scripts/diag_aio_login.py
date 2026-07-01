"""Diagnostico de autenticacao AIO e extracao de participantes."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from scrape_aio_escolas import (
    AioClient,
    _extrair_nome_escola_history,
    _parse_participantes_historico_logado,
    _tabelas_tem_coluna_participantes,
    enriquecer_com_login,
    parsear_pagina_escola,
)

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

session = os.getenv("AIO_SESSION")
email = os.getenv("AIO_EMAIL")
password = os.getenv("AIO_PASSWORD")
inep = int(sys.argv[1]) if len(sys.argv) > 1 else 50000675

if session:
    client = AioClient(session_cookie=session)
    print("modo: cookie")
elif email and password:
    client = AioClient(email=email, password=password)
    print("modo: email/senha")
else:
    raise SystemExit("Defina AIO_SESSION ou AIO_EMAIL/AIO_PASSWORD no .env")

print("sessao_valida:", client.authenticated)
if not client.authenticated:
    raise SystemExit("Sessao invalida. Copie um cookie _aio_session novo do navegador.")

html_pub = client.pagina_escola(inep)
escola = parsear_pagina_escola(html_pub, inep)
print("escola_publica:", escola.nome, f"(INEP {escola.co_inep})")

vinculada = client.escola_vinculada_id()
internal_id = client.resolver_aio_school_id(inep)
print("aio_internal_id:", internal_id)
print("escola_vinculada_conta:", vinculada)

hist = client.historico_logado(inep)
history_nome = _extrair_nome_escola_history(hist) if hist else ""
print("history_len:", len(hist))
print("history_escola_exibida:", history_nome or "(vazio)")
print("history_tem_coluna_participantes:", _tabelas_tem_coluna_participantes(hist))
print(
    "particip_no_html (texto rodape, nao e dado):",
    bool(hist) and "particip" in hist.lower() and not _tabelas_tem_coluna_participantes(hist),
)

if hist:
    parsed_hist = _parse_participantes_historico_logado(hist)
    print("participantes_parseados_history:", parsed_hist)

classif = client.classificacao_logado()
print("classificacao_len:", len(classif))
if escola.nome and vinculada:
    part_classif = client.participantes_por_ano_logado(escola.nome)
    print("participantes_classificacao (escola vinculada):", part_classif)

escola = enriquecer_com_login(client, escola, debug_dir=ROOT / "dados" / "aio" / "debug_aio")
print("participantes_finais:", escola.participantes_por_ano)
print("anos_historico:", len(escola.historico))

if hist:
    (ROOT / "dados" / "aio" / "debug_aio" / f"history_{inep}.html").write_text(hist, encoding="utf-8")
    print("html salvo em dados/aio/debug_aio/")

if history_nome and escola.nome and history_nome.lower() not in escola.nome.lower() and escola.nome.lower() not in history_nome.lower():
    print()
    print("AVISO: /school_enem_data/history ignora school_id=INEP e mostra a escola vinculada a conta.")
    print("Participantes (coluna Alunos) so aparecem na aba Classificacao, para a escola vinculada.")
    print("Notas/historico de qualquer INEP continuam disponiveis na pagina publica (sem login).")
