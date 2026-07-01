"""
Extrai dados ENEM por escola da AIO (aio.com.br) usando codigos INEP.

A pagina publica /enem-por-escola/escola/{CO_INEP} traz:
  - medias por area (ultimo ano disponivel)
  - historico 2013-2025 (grafico em data-chart-data-value)
  - rankings municipio, UF e Brasil (ultimo ano)
  - rede administrativa (Federal, Estadual, Municipal, Privada)

Descoberta de escolas via API publica:
  GET /api/v1/schools/autocomplete?q={consulta}

Uso:
  python scripts/scrape_aio_escolas.py --rede Estadual
  python scripts/scrape_aio_escolas.py --pdf-estaduais "C:/caminho/escolas.pdf"
  python scripts/scrape_aio_escolas.py --comparar-pdf --pdf-estaduais "C:/caminho/escolas.pdf"
  python scripts/scrape_aio_escolas.py --com-login --inep-list dados/aio/ineps_pdf_estaduais.txt
  python scripts/scrape_aio_escolas.py --inep 50005626 50000675
  python scripts/scrape_aio_escolas.py --completar-participantes-parquet
  python scripts/aio_participantes_parquet.py
"""
from __future__ import annotations

import argparse
import csv
import html as html_lib
import http.cookiejar
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from enem_config import PASTA_DADOS, configure_logging

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PIPELINE_ROOT / ".env"

try:
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)
    load_dotenv()
except ImportError:
    pass

logger = configure_logging(__name__)

AIO_BASE = "https://www.aio.com.br"
AUTOCOMPLETE_URL = f"{AIO_BASE}/api/v1/schools/autocomplete"
ESCOLA_URL = f"{AIO_BASE}/enem-por-escola/escola/{{inep}}"
HISTORY_URL = f"{AIO_BASE}/school_enem_data/history"
CLASSIFICACAO_URL = f"{AIO_BASE}/school_enem_data/classificacao"
RANKING_URL = f"{AIO_BASE}/school_enem_data/ranking"
SIGN_IN_URL = f"{AIO_BASE}/users/sign_in"
SAIDA_PADRAO = PASTA_DADOS / "aio"
PDF_ESTADUAIS_PADRAO = Path(
    r"C:\Users\User\Downloads\Contatos e Endereços das Escolas_Estaduais_Fev_2025 com códigos inep.pdf"
)

AREA_MAP = {
    "Linguagens": "NU_NOTA_LC",
    "Ciências Humanas": "NU_NOTA_CH",
    "Ciencias Humanas": "NU_NOTA_CH",
    "Ciências da Natureza": "NU_NOTA_CN",
    "Ciencias da Natureza": "NU_NOTA_CN",
    "Matemática": "NU_NOTA_MT",
    "Matematica": "NU_NOTA_MT",
    "Redação": "NU_NOTA_REDACAO",
    "Redacao": "NU_NOTA_REDACAO",
}

CARD_LABELS = {
    "Linguagens": "NU_NOTA_LC",
    "Ciências Humanas": "NU_NOTA_CH",
    "Ciências da Natureza": "NU_NOTA_CN",
    "Matemática": "NU_NOTA_MT",
    "Redação": "NU_NOTA_REDACAO",
}

MUNICIPIOS_MS = [
    "Agua Clara",
    "Alcinopolis",
    "Amambai",
    "Anastacio",
    "Anaurilandia",
    "Angelica",
    "Antonio Joao",
    "Aparecida do Taboado",
    "Aquidauana",
    "Aral Moreira",
    "Bandeirantes",
    "Bataguassu",
    "Bataipora",
    "Bela Vista",
    "Bodoquena",
    "Bonito",
    "Brasilandia",
    "Caarapo",
    "Camapua",
    "Campo Grande",
    "Caracol",
    "Cassilandia",
    "Chapadao do Sul",
    "Corguinho",
    "Coronel Sapucaia",
    "Corumba",
    "Costa Rica",
    "Coxim",
    "Deodapolis",
    "Dois Irmaos do Buriti",
    "Douradina",
    "Dourados",
    "Eldorado",
    "Fatima do Sul",
    "Figueirao",
    "Gloria de Dourados",
    "Guia Lopes da Laguna",
    "Iguatemi",
    "Inocencia",
    "Itapora",
    "Itaquirai",
    "Ivinhema",
    "Japora",
    "Jaraguari",
    "Jardim",
    "Jatei",
    "Juti",
    "Ladario",
    "Laguna Carapa",
    "Maracaju",
    "Miranda",
    "Mundo Novo",
    "Navirai",
    "Nioaque",
    "Nova Alvorada do Sul",
    "Nova Andradina",
    "Novo Horizonte do Sul",
    "Paranaiba",
    "Paranhos",
    "Pedro Gomes",
    "Ponta Pora",
    "Porto Murtinho",
    "Ribas do Rio Pardo",
    "Rio Brilhante",
    "Rio Negro",
    "Rio Verde de Mato Grosso",
    "Rochedo",
    "Santa Rita do Pardo",
    "Sao Gabriel do Oeste",
    "Selviria",
    "Sete Quedas",
    "Sidrolandia",
    "Sonora",
    "Tacuru",
    "Taquarussu",
    "Terenos",
    "Tres Lagoas",
    "Vicentina",
]


@dataclass
class EscolaAio:
    co_inep: int
    nome: str = ""
    nome_autocomplete: str = ""
    rede: str = ""
    municipio: str = ""
    uf: str = "MS"
    ranking_municipio: int | None = None
    ranking_uf: int | None = None
    ranking_brasil: int | None = None
    ranking_municipio_label: str = ""
    medias_ultimo_ano: dict[str, float] = field(default_factory=dict)
    ano_ultimo: int | None = None
    historico: list[dict] = field(default_factory=list)
    participantes_por_ano: dict[int, int] = field(default_factory=dict)
    aio_school_id: int | None = None
    erro: str = ""


class AioClient:
    def __init__(
        self,
        delay: float = 0.35,
        timeout: float = 25.0,
        email: str | None = None,
        password: str | None = None,
        session_cookie: str | None = None,
    ):
        self.delay = delay
        self.timeout = timeout
        self._last_request = 0.0
        self._authenticated = False
        self._school_id_cache: dict[int, int] = {}
        self._csrf_token_cache: str | None = None
        self._escola_vinculada_id: int | None = None
        self._cookie_jar = http.cookiejar.CookieJar()
        self._auth_opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookie_jar)
        )
        # Paginas publicas nao devem levar cookie de sessao (evita 401 em massa).
        self._public_opener = urllib.request.build_opener()
        if session_cookie:
            self.use_session_cookie(session_cookie)
        elif email and password:
            self.login(email, password)

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    def use_session_cookie(self, value: str) -> None:
        """Usa cookie _aio_session copiado do navegador (F12 > Application > Cookies)."""
        value = value.strip()
        if value.startswith("_aio_session="):
            value = value.split("=", 1)[1].strip()
        for domain in ("www.aio.com.br", ".aio.com.br"):
            self._cookie_jar.set_cookie(
                http.cookiejar.Cookie(
                    version=0,
                    name="_aio_session",
                    value=value,
                    port=None,
                    port_specified=False,
                    domain=domain,
                    domain_specified=True,
                    domain_initial_dot=domain.startswith("."),
                    path="/",
                    path_specified=True,
                    secure=True,
                    expires=None,
                    discard=True,
                    comment=None,
                    comment_url=None,
                    rest={"HttpOnly": None},
                    rfc2109=False,
                )
            )
        self._authenticated = self._sessao_valida()
        if not self._authenticated:
            raise RuntimeError(
                "Cookie _aio_session invalido ou expirado. "
                "Faca login em https://www.aio.com.br no navegador, copie o cookie novamente "
                "(F12 > Application > Cookies > www.aio.com.br > _aio_session)."
            )
        logger.info("Sessao AIO OK via cookie _aio_session")

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _request(
        self,
        url: str,
        *,
        accept: str = "*/*",
        method: str = "GET",
        data: bytes | None = None,
        referer: str | None = None,
        turbo_frame: str | None = None,
        content_type: str | None = None,
        origin: str | None = None,
        csrf_token: str | None = None,
        allow_http_error: bool = False,
        authenticated: bool = False,
    ) -> tuple[bytes, int]:
        self._wait()
        headers = {
            "User-Agent": "enem-dashboard-aio-scraper/1.0",
            "Accept": accept,
        }
        if referer:
            headers["Referer"] = referer
        if turbo_frame:
            headers["Turbo-Frame"] = turbo_frame
        if content_type:
            headers["Content-Type"] = content_type
        if origin:
            headers["Origin"] = origin
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        opener = self._auth_opener if authenticated else self._public_opener
        try:
            with opener.open(req, timeout=self.timeout) as resp:
                self._last_request = time.monotonic()
                chunks: list[bytes] = []
                while True:
                    part = resp.read(65536)
                    if not part:
                        break
                    chunks.append(part)
                return b"".join(chunks), resp.status
        except urllib.error.HTTPError as exc:
            self._last_request = time.monotonic()
            body = exc.read()
            if allow_http_error:
                return body, exc.code
            if exc.code in (401, 404):
                return b"", exc.code
            raise

    def get(self, url: str, accept: str = "*/*", *, authenticated: bool = False, **kwargs) -> bytes:
        body, _ = self._request(url, accept=accept, authenticated=authenticated, **kwargs)
        return body

    def _html_eh_login(self, html: str) -> bool:
        if not html:
            return True
        lower = html.lower()
        if "sign_in_card" in lower or 'id="sign_in"' in lower:
            return True
        if "email ou senha inv" in lower:
            return True
        if "/users/sign_in" in lower and "painel de desempenho" not in lower:
            if "school_enem_data" not in lower and "particip" not in lower:
                return True
        return False

    def _csrf_token(self) -> str | None:
        if self._csrf_token_cache:
            return self._csrf_token_cache
        html = self.get(f"{AIO_BASE}/school_enem_data/history", accept="text/html", authenticated=True).decode(
            "utf-8", "replace"
        )
        meta = re.search(r'name="csrf-token" content="([^"]+)"', html)
        self._csrf_token_cache = meta.group(1) if meta else None
        return self._csrf_token_cache

    def _sessao_valida(self) -> bool:
        html = self.get(
            f"{HISTORY_URL}?school_id=50000675",
            accept="text/html, application/xhtml+xml",
            authenticated=True,
        ).decode("utf-8", "replace")
        if self._html_eh_login(html):
            return False
        return any(
            token in html.lower()
            for token in ("particip", "school_enem_data/history", "histórico", "historico", "data-chart-data-value")
        )

    def _extrair_school_id_html(self, html: str) -> int | None:
        patterns = [
            r"school_enem_data/classificacao\?school_id=(\d+)",
            r"school_enem_data/history\?school_id=(\d+)",
            r'data-school-id="(\d+)"',
            r'"school_id"\s*:\s*(\d+)',
            r"'school_id'\s*=>\s*(\d+)",
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                sid = int(m.group(1))
                if sid < 10_000_000:
                    return sid
        return None

    def login(self, email: str, password: str) -> None:
        login_html = self.get(SIGN_IN_URL, accept="text/html", authenticated=True).decode(
            "utf-8", "replace"
        )
        token_m = re.search(r'name="authenticity_token" value="([^"]+)"', login_html)
        meta_m = re.search(r'name="csrf-token" content="([^"]+)"', login_html)
        if not token_m:
            raise RuntimeError("Nao foi possivel obter authenticity_token da pagina de login AIO.")
        token = token_m.group(1)
        payload = urllib.parse.urlencode(
            {
                "authenticity_token": token,
                "user[email]": email,
                "user[password]": password,
                "user[remember_me]": "0",
            }
        ).encode("utf-8")
        body, status = self._request(
            SIGN_IN_URL,
            accept="text/html, application/xhtml+xml",
            method="POST",
            data=payload,
            allow_http_error=True,
            referer=SIGN_IN_URL,
            content_type="application/x-www-form-urlencoded",
            origin=AIO_BASE,
            csrf_token=meta_m.group(1) if meta_m else None,
            authenticated=True,
        )
        body_text = body.decode("utf-8", "replace")
        if status == 422 or "Email ou senha inv" in body_text:
            raise RuntimeError(
                "Login AIO recusado: e-mail ou senha invalidos. "
                "Se voce entra pela conta Google, use o cookie do navegador: "
                "--aio-session ou AIO_SESSION no .env (veja instrucoes no README). "
                "No PowerShell use aspas simples na senha: --aio-password 'sua_senha'."
            )
        self._authenticated = self._sessao_valida()
        if not self._authenticated:
            raise RuntimeError(
                "Login AIO nao liberou acesso ao historico. "
                "Confirme as credenciais ou se a conta tem acesso ao painel escolar."
            )
        logger.info("Login AIO OK (%s)", email)

    def resolver_aio_school_id(self, co_inep: int) -> int | None:
        if co_inep in self._school_id_cache:
            return self._school_id_cache[co_inep]
        if not self._authenticated:
            return None

        sid: int | None = None
        api_urls = [
            f"{AIO_BASE}/api/v1/schools/{co_inep}",
            f"{AIO_BASE}/api/v1/schools/{co_inep}.json",
            f"{AIO_BASE}/api/v1/schools/find_by_inep/{co_inep}",
        ]
        for url in api_urls:
            body, status = self._request(
                url,
                accept="application/json",
                authenticated=True,
                csrf_token=self._csrf_token(),
                allow_http_error=True,
            )
            if status != 200 or not body:
                continue
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            candidates = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                for key in ("id", "school_id", "aio_school_id"):
                    val = item.get(key)
                    if val is not None and int(val) < 10_000_000:
                        sid = int(val)
                        break
                if sid is None and isinstance(item.get("school"), dict):
                    val = item["school"].get("id")
                    if val is not None and int(val) < 10_000_000:
                        sid = int(val)
                if sid is not None:
                    break
            if sid is not None:
                break

        if sid is None:
            auth_escola = self.get(
                f"{ESCOLA_URL.format(inep=co_inep)}?no_cta=true",
                accept="text/html",
                authenticated=True,
            ).decode("utf-8", "replace")
            sid = self._extrair_school_id_html(auth_escola)

        if sid is None:
            hist_html = self.get(HISTORY_URL, accept="text/html", authenticated=True).decode(
                "utf-8", "replace"
            )
            sid = _extrair_internal_id_colecao(hist_html, co_inep)

        if sid is not None:
            self._school_id_cache[co_inep] = sid
        return sid

    def historico_logado(self, co_inep: int) -> str:
        if not self._authenticated:
            return ""
        school_id = self.resolver_aio_school_id(co_inep)
        if school_id is None:
            return ""

        referer = ESCOLA_URL.format(inep=co_inep)
        attempts: list[tuple[str, dict]] = [
            (f"{HISTORY_URL}?{urllib.parse.urlencode({'school_id': school_id})}", {}),
            (f"{HISTORY_URL}?{urllib.parse.urlencode({'school_id': co_inep})}", {}),
            (HISTORY_URL, {}),
            (
                f"{HISTORY_URL}?{urllib.parse.urlencode({'school_id': school_id})}",
                {"turbo_frame": "school_enem_data_history"},
            ),
            (
                f"{HISTORY_URL}?{urllib.parse.urlencode({'school_id': school_id})}",
                {"turbo_frame": "history"},
            ),
            (
                f"{AIO_BASE}/school_enem_data/classificacao?{urllib.parse.urlencode({'school_id': school_id})}",
                {"turbo_frame": "all_ranking"},
            ),
        ]
        best = ""
        for url, extra in attempts:
            body, status = self._request(
                url,
                accept="text/html, application/xhtml+xml",
                referer=referer,
                authenticated=True,
                allow_http_error=True,
                **extra,
            )
            html = body.decode("utf-8", "replace") if body else ""
            if status not in (200, 204) or self._html_eh_login(html):
                continue
            if "particip" in html.lower() or "data-chart-data-value" in html:
                return html
            if len(html) > len(best):
                best = html
        return best

    def escola_vinculada_id(self) -> int | None:
        if self._escola_vinculada_id is not None:
            return self._escola_vinculada_id
        if not self._authenticated:
            return None
        html = self.get(HISTORY_URL, accept="text/html", authenticated=True).decode("utf-8", "replace")
        self._escola_vinculada_id = _extrair_escola_vinculada_id(html)
        return self._escola_vinculada_id

    def classificacao_logado(self) -> str:
        if not self._authenticated:
            return ""
        sid = self.escola_vinculada_id()
        url = f"{CLASSIFICACAO_URL}?{urllib.parse.urlencode({'school_id': sid})}" if sid else CLASSIFICACAO_URL
        body, status = self._request(
            url,
            accept="text/html, application/xhtml+xml",
            authenticated=True,
            allow_http_error=True,
        )
        html = body.decode("utf-8", "replace") if body else ""
        return html if status == 200 and not self._html_eh_login(html) else ""

    def participantes_por_ano_logado(self, nome_escola: str) -> dict[int, int]:
        """Participantes via aba Classificacao (escola vinculada a conta)."""
        if not self._authenticated or not nome_escola:
            return {}
        sid = self.escola_vinculada_id()
        if sid is None:
            return {}
        classif = self.classificacao_logado()
        out = _parse_participantes_classificacao(classif, nome_escola)
        token_m = re.search(r'name="authenticity_token" value="([^"]+)"', classif)
        if not token_m:
            return out
        token = token_m.group(1)
        csrf = self._csrf_token()
        for ano in range(2013, 2026):
            if ano in out:
                continue
            payload = urllib.parse.urlencode(
                {
                    "authenticity_token": token,
                    "school_id": str(sid),
                    "school_type": "all",
                    "year": str(ano),
                    "score_type": "all",
                    "slice": "10..",
                }
            ).encode("utf-8")
            body, status = self._request(
                RANKING_URL,
                accept="text/html, application/xhtml+xml",
                method="POST",
                data=payload,
                referer=f"{CLASSIFICACAO_URL}?school_id={sid}",
                turbo_frame="all_ranking",
                content_type="application/x-www-form-urlencoded",
                csrf_token=csrf,
                authenticated=True,
                allow_http_error=True,
            )
            html = body.decode("utf-8", "replace") if body else ""
            if status != 200 or self._html_eh_login(html) or "Aconteceu um problema" in html:
                continue
            parsed = _parse_participantes_classificacao(html, nome_escola, ano=ano)
            if ano in parsed:
                out[ano] = parsed[ano]
        return out

    def autocomplete(self, query: str) -> list[tuple[str, int]]:
        url = f"{AUTOCOMPLETE_URL}?{urllib.parse.urlencode({'q': query})}"
        raw = self.get(url, accept="application/json")
        if not raw:
            return []
        data = json.loads(raw.decode("utf-8"))
        out: list[tuple[str, int]] = []
        for item in data:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            label, inep = item[0], item[1]
            try:
                co = int(inep)
            except (TypeError, ValueError):
                continue
            if str(co).startswith("50"):
                out.append((str(label), co))
        return out

    def pagina_escola(self, co_inep: int) -> str:
        url = ESCOLA_URL.format(inep=co_inep)
        raw = self.get(url, accept="text/html", authenticated=False)
        return raw.decode("utf-8", "replace") if raw else ""


def descobrir_escolas_ms(client: AioClient, cache_path: Path | None = None) -> dict[int, str]:
    if cache_path and cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        logger.info("Cache de descoberta: %s escolas (%s)", len(cached), cache_path)
        return {int(k): v for k, v in cached.items()}

    escolas: dict[int, str] = {}

    for i in range(100):
        for label, inep in client.autocomplete(f"500{i:02d}"):
            escolas[inep] = label

    for municipio in MUNICIPIOS_MS:
        for label, inep in client.autocomplete(municipio):
            escolas[inep] = label

    logger.info("Descobertas %s escolas MS via autocomplete AIO", len(escolas))
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({str(k): v for k, v in sorted(escolas.items())}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return escolas


def _parse_ranking(html: str) -> tuple[int | None, int | None, int | None, str]:
    ranking_mun = ranking_uf = ranking_br = None
    mun_label = ""
    rows = re.findall(
        r'<div class="text-sm text-muted">([^<]+)</div>\s*'
        r'<div class="text-sm font-black text-primary">#(\d+)\s+(?:em|no)\s+([^<]+)</div>',
        html,
    )
    for label, pos, scope in rows:
        n = int(pos)
        label_l = label.lower()
        scope_l = scope.strip().lower()
        if label_l.startswith("cidade") or "municip" in label_l:
            ranking_mun = n
            mun_label = scope.strip()
        elif label_l.startswith("estado") or scope_l in {"ms", "mt", "sp", "rj"}:
            ranking_uf = n
        elif "brasil" in label_l or "brasil" in scope_l:
            ranking_br = n
    return ranking_mun, ranking_uf, ranking_br, mun_label


def _parse_cards_ultimo_ano(html: str) -> dict[str, float]:
    medias: dict[str, float] = {}
    blocks = re.findall(
        r'<div class="text-xs text-muted font-medium uppercase tracking-wider mb-1">([^<]+)</div>\s*'
        r'<div class="text-2xl font-black text-default">([\d.]+)</div>',
        html,
    )
    for label, valor in blocks:
        label = label.strip()
        col = CARD_LABELS.get(label)
        if col:
            medias[col] = float(valor)
    return medias


def _parse_historico(html: str) -> list[dict]:
    m = re.search(r'data-chart-data-value="([^"]+)"', html)
    if not m:
        return []
    series = json.loads(html_lib.unescape(m.group(1)))
    por_ano: dict[int, dict] = {}
    for serie in series:
        nome = serie.get("name", "")
        col = AREA_MAP.get(nome)
        if not col:
            continue
        for ponto in serie.get("data", []):
            ano = int(ponto["x"])
            y = ponto.get("y")
            if y is None:
                continue
            nota = float(y)
            row = por_ano.setdefault(ano, {"NU_ANO": ano})
            row[col] = nota
    historico = []
    for ano in sorted(por_ano):
        row = por_ano[ano]
        notas = [row[c] for c in CARD_LABELS.values() if c in row]
        if notas:
            row["MEDIA_GERAL"] = round(sum(notas) / len(notas), 2)
        historico.append(row)
    return historico


def _strip_html(text: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", text)).strip()


def _normalizar_nome_escola(nome: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(nome)).strip().lower()


def _extrair_internal_id_colecao(html: str, co_inep: int) -> int | None:
    m = re.search(r'data-searchinput-collection="([^"]+)"', html)
    if not m:
        return None
    try:
        coll = json.loads(html_lib.unescape(m.group(1)))
    except json.JSONDecodeError:
        return None
    prefix = str(co_inep)
    for label, sid in coll:
        if str(label).startswith(prefix):
            try:
                return int(sid)
            except (TypeError, ValueError):
                continue
    return None


def _extrair_nome_escola_history(html: str) -> str:
    m = re.search(r"Escola:\s*([^<\n]+)", html)
    return m.group(1).strip() if m else ""


def _extrair_escola_vinculada_id(html: str) -> int | None:
    m = re.search(r"school_enem_data/history\?school_id=(\d+)", html)
    if not m:
        return None
    sid = int(m.group(1))
    return sid if sid < 10_000_000 else None


def _tabelas_tem_coluna_participantes(html: str) -> bool:
    for table in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        headers = [_strip_html(h).lower() for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S | re.I)]
        if any("particip" in h or h == "alunos" for h in headers):
            return True
    return False


def _nomes_escola_coincidem(a: str, b: str) -> bool:
    na, nb = _normalizar_nome_escola(a), _normalizar_nome_escola(b)
    if not na or not nb:
        return False
    return na in nb or nb in na


def _parse_participantes_classificacao(html: str, nome_escola: str, ano: int | None = None) -> dict[int, int]:
    """Extrai {ano: n_alunos} das tabelas de ranking com coluna Alunos."""
    if not html or not nome_escola:
        return {}
    alvo = _normalizar_nome_escola(nome_escola)
    out: dict[int, int] = {}
    if ano is None:
        year_m = re.search(r'<select[^>]*id="year"[^>]*>.*?value="(\d{4})"\s*selected', html, re.S | re.I)
        ano = int(year_m.group(1)) if year_m else None
    for table in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        headers = [_strip_html(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S | re.I)]
        if not headers:
            continue
        headers_l = [h.lower() for h in headers]
        try:
            alunos_idx = next(i for i, h in enumerate(headers_l) if h == "alunos" or "particip" in h)
        except StopIteration:
            continue
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I):
            cells = [_strip_html(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
            if len(cells) <= alunos_idx:
                continue
            nome_cel = _normalizar_nome_escola(cells[1] if len(cells) > 1 else cells[0])
            if alvo not in nome_cel and nome_cel not in alvo:
                continue
            part_m = re.search(r"(\d+)", cells[alunos_idx].replace(".", ""))
            if not part_m or ano is None:
                continue
            out[ano] = int(part_m.group(1))
            break
        if out:
            break
    return out


def _parse_participantes_chart(html: str) -> dict[int, int]:
    out: dict[int, int] = {}
    for m in re.finditer(r'data-chart-data-value="([^"]+)"', html):
        try:
            series = json.loads(html_lib.unescape(m.group(1)))
        except json.JSONDecodeError:
            continue
        for serie in series:
            nome = str(serie.get("name", "")).lower()
            if not re.search(r"particip|aluno|estud|inscrit", nome):
                continue
            for ponto in serie.get("data", []):
                ano_m = re.search(r"(20\d{2})", str(ponto.get("x", "")))
                y = ponto.get("y")
                if ano_m and y is not None:
                    out[int(ano_m.group(1))] = int(float(y))
    return out


def _parse_participantes_historico_logado(html: str) -> dict[int, int]:
    """Extrai {ano: n_participantes} do HTML autenticado /school_enem_data/history."""
    if not html:
        return {}
    out = _parse_participantes_chart(html)
    if out:
        return out
    for table in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        headers = [_strip_html(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S | re.I)]
        if not headers:
            first_row = re.search(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I)
            if first_row:
                headers = [
                    _strip_html(c)
                    for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", first_row.group(1), re.S | re.I)
                ]
        if not headers:
            continue
        headers_l = [h.lower() for h in headers]
        try:
            ano_idx = next(i for i, h in enumerate(headers_l) if "ano" in h)
            part_idx = next(i for i, h in enumerate(headers_l) if "particip" in h)
        except StopIteration:
            continue
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I)
        start = 1 if rows and "<th" in rows[0].lower() else 0
        for row in rows[start:]:
            cells = [_strip_html(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
            if len(cells) <= max(ano_idx, part_idx):
                continue
            ano_m = re.search(r"(20\d{2})", cells[ano_idx])
            part_m = re.search(r"(\d+)", cells[part_idx].replace(".", ""))
            if ano_m and part_m:
                out[int(ano_m.group(1))] = int(part_m.group(1))

    if not out:
        for ano, qtd in re.findall(
            r"(20\d{2})[^0-9]{0,80}(?:particip[a-z]*|inscritos?|alunos?)[^0-9]{0,20}(\d{1,5})",
            html,
            re.I,
        ):
            out[int(ano)] = int(qtd)
    return out


def _parse_participantes_div_grid(html: str) -> dict[int, int]:
    """Fallback: blocos HTML com ano e quantidade de participantes."""
    out: dict[int, int] = {}
    for block in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S | re.I):
        if "particip" not in block.lower():
            continue
        cells = [_strip_html(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", block, re.S | re.I)]
        anos = [int(m.group(1)) for c in cells for m in re.finditer(r"(20\d{2})", c)]
        nums = [int(m.group(1)) for c in cells for m in re.finditer(r"\b(\d{1,4})\b", c)]
        if anos and nums:
            out[anos[0]] = max(n for n in nums if n <= 5000)
    return out


def _parse_historico_logado_tabela(html: str) -> list[dict]:
    """Tenta extrair medias/participantes por ano de tabelas no painel autenticado."""
    rows_out: list[dict] = []
    col_map = {
        "linguagens": "NU_NOTA_LC",
        "humanas": "NU_NOTA_CH",
        "natureza": "NU_NOTA_CN",
        "matem": "NU_NOTA_MT",
        "reda": "NU_NOTA_REDACAO",
        "geral": "MEDIA_GERAL",
        "particip": "N_PARTICIPANTES",
    }
    for table in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        headers = [_strip_html(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S | re.I)]
        if not headers or not any("ano" in h.lower() for h in headers):
            continue
        idx = {}
        for i, h in enumerate(headers):
            hl = h.lower()
            if "ano" in hl:
                idx["NU_ANO"] = i
            for needle, col in col_map.items():
                if needle in hl:
                    idx[col] = i
        if "NU_ANO" not in idx:
            continue
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I)[1:]:
            cells = [_strip_html(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
            if len(cells) <= idx["NU_ANO"]:
                continue
            ano_m = re.search(r"(20\d{2})", cells[idx["NU_ANO"]])
            if not ano_m:
                continue
            item: dict = {"NU_ANO": int(ano_m.group(1))}
            for col, i in idx.items():
                if col == "NU_ANO" or i >= len(cells):
                    continue
                num_m = re.search(r"([\d]+(?:[.,]\d+)?)", cells[i])
                if not num_m:
                    continue
                val = float(num_m.group(1).replace(",", "."))
                item[col] = int(val) if col == "N_PARTICIPANTES" else val
            if len(item) > 1:
                rows_out.append(item)
    return rows_out


def _mesclar_historico(
    publico: list[dict],
    logado: list[dict],
    participantes: dict[int, int],
) -> list[dict]:
    por_ano: dict[int, dict] = {r["NU_ANO"]: dict(r) for r in publico}
    for row in logado:
        ano = row["NU_ANO"]
        base = por_ano.setdefault(ano, {"NU_ANO": ano})
        base.update({k: v for k, v in row.items() if v is not None and k != "NU_ANO"})
    for ano, qtd in participantes.items():
        por_ano.setdefault(ano, {"NU_ANO": ano})["N_PARTICIPANTES"] = qtd
    historico = []
    for ano in sorted(por_ano):
        row = por_ano[ano]
        notas = [row[c] for c in CARD_LABELS.values() if c in row and row[c] is not None]
        if notas and "MEDIA_GERAL" not in row:
            row["MEDIA_GERAL"] = round(sum(notas) / len(notas), 2)
        historico.append(row)
    return historico


def parsear_pagina_escola(html: str, co_inep: int, nome_autocomplete: str = "") -> EscolaAio:
    escola = EscolaAio(co_inep=co_inep, nome_autocomplete=nome_autocomplete)
    if not html or "Painel de Desempenho" not in html:
        escola.erro = "sem_painel"
        return escola

    nome_m = re.search(
        r'Painel de Desempenho:\s*<span class="text-primary">([^<]+)</span>',
        html,
    )
    if nome_m:
        escola.nome = html_lib.unescape(nome_m.group(1).strip())

    rede_m = re.search(
        r'rounded-full px-3 py-1 text-xs font-medium bg-[^"\']+[^>]*>\s*'
        r"(Privada|Estadual|Municipal|Federal)",
        html,
    )
    if rede_m:
        escola.rede = rede_m.group(1)

    loc_m = re.search(
        r'rounded-full px-3 py-1 text-xs font-medium bg-surface-subtle text-muted">\s*'
        r"([^<]+?)\s*—\s*([A-Z]{2})\s*",
        html,
    )
    if loc_m:
        escola.municipio = html_lib.unescape(loc_m.group(1).strip())
        escola.uf = loc_m.group(2).strip()

    inep_m = re.search(r"Código INEP:\s*<strong>(\d+)</strong>", html)
    if inep_m:
        escola.co_inep = int(inep_m.group(1))

    escola.ranking_municipio, escola.ranking_uf, escola.ranking_brasil, escola.ranking_municipio_label = (
        _parse_ranking(html)
    )
    escola.medias_ultimo_ano = _parse_cards_ultimo_ano(html)
    escola.historico = _parse_historico(html)
    if escola.historico:
        escola.ano_ultimo = max(r["NU_ANO"] for r in escola.historico)
    return escola


def enriquecer_com_login(client: AioClient, escola: EscolaAio, debug_dir: Path | None = None) -> EscolaAio:
    if not client.authenticated or escola.erro:
        return escola

    escola.aio_school_id = client.resolver_aio_school_id(escola.co_inep)
    vinculada_id = client.escola_vinculada_id()
    history_html = client.historico_logado(escola.co_inep)
    history_nome = _extrair_nome_escola_history(history_html) if history_html else ""
    mesma_escola = _nomes_escola_coincidem(history_nome, escola.nome)

    if debug_dir and history_html:
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f"history_{escola.co_inep}.html").write_text(history_html, encoding="utf-8")

    participantes: dict[int, int] = {}
    if mesma_escola:
        participantes = _parse_participantes_historico_logado(history_html)
        if not participantes:
            participantes = client.participantes_por_ano_logado(escola.nome)
    elif vinculada_id is not None and escola.aio_school_id == vinculada_id:
        participantes = client.participantes_por_ano_logado(escola.nome)
    else:
        logger.info(
            "  %s: painel autenticado e da escola vinculada (%s); "
            "participantes AIO nao disponiveis para esta escola via login generico",
            escola.co_inep,
            history_nome or vinculada_id,
        )

    if participantes:
        escola.participantes_por_ano = participantes

    if mesma_escola and history_html:
        logado = _parse_historico_logado_tabela(history_html)
        if logado or participantes:
            escola.historico = _mesclar_historico(escola.historico, logado, participantes)
            if escola.historico:
                escola.ano_ultimo = max(r["NU_ANO"] for r in escola.historico)
    elif participantes:
        escola.historico = _mesclar_historico(escola.historico, [], participantes)

    return escola


def escola_para_linhas(escola: EscolaAio) -> list[dict]:
    if not escola.historico:
        return [{
            "CO_INEP": escola.co_inep,
            "NOME_ESCOLA": escola.nome,
            "REDE": escola.rede,
            "MUNICIPIO": escola.municipio,
            "UF": escola.uf,
            "NU_ANO": escola.ano_ultimo,
            "RANKING_MUNICIPIO": escola.ranking_municipio,
            "RANKING_UF": escola.ranking_uf,
            "RANKING_BRASIL": escola.ranking_brasil,
            "ERRO": escola.erro or "sem_historico",
        }]

    linhas = []
    ultimo = escola.ano_ultimo
    for row in escola.historico:
        linha = {
            "CO_INEP": escola.co_inep,
            "NOME_ESCOLA": escola.nome,
            "NOME_AUTOCOMPLETE": escola.nome_autocomplete,
            "REDE": escola.rede,
            "MUNICIPIO": escola.municipio,
            "UF": escola.uf,
            "NU_ANO": row["NU_ANO"],
            "NU_NOTA_LC": row.get("NU_NOTA_LC"),
            "NU_NOTA_CH": row.get("NU_NOTA_CH"),
            "NU_NOTA_CN": row.get("NU_NOTA_CN"),
            "NU_NOTA_MT": row.get("NU_NOTA_MT"),
            "NU_NOTA_REDACAO": row.get("NU_NOTA_REDACAO"),
            "MEDIA_GERAL": row.get("MEDIA_GERAL"),
            "N_PARTICIPANTES": row.get("N_PARTICIPANTES"),
        }
        if row["NU_ANO"] == ultimo:
            linha["RANKING_MUNICIPIO"] = escola.ranking_municipio
            linha["RANKING_UF"] = escola.ranking_uf
            linha["RANKING_BRASIL"] = escola.ranking_brasil
        linhas.append(linha)
    return linhas


def carregar_ineps_arquivo(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8")
    ineps: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = re.split(r"[,;\s]+", line)[0]
        if token.isdigit():
            ineps.append(int(token))
    return ineps


def salvar_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        logger.warning("Nenhuma linha para salvar em %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    for row in rows[1:]:
        for k in row:
            if k not in cols:
                cols.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def extrair_ineps_pdf(pdf_path: Path) -> list[int]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("Instale pdfplumber para ler o PDF: pip install pdfplumber") from exc
    text_parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts)
    return sorted({int(m) for m in re.findall(r"\b(50\d{6})\b", text)})


def comparar_pdf_aio(pdf_path: Path, saida: Path) -> dict:
    pdf_ineps = set(extrair_ineps_pdf(pdf_path))
    aio_cache = saida / "escolas_ms_descobertas.json"
    aio_ineps: set[int] = set()
    if aio_cache.exists():
        aio_ineps = set(map(int, json.loads(aio_cache.read_text(encoding="utf-8"))))

    com_painel: list[int] = []
    sem_painel: list[int] = []
    client = AioClient(delay=0.2)
    for inep in sorted(pdf_ineps - aio_ineps):
        html = client.pagina_escola(inep)
        if "Painel de Desempenho" in html:
            com_painel.append(inep)
        else:
            sem_painel.append(inep)

    relatorio = {
        "pdf_total": len(pdf_ineps),
        "no_autocomplete_aio": len(pdf_ineps & aio_ineps),
        "fora_autocomplete": len(pdf_ineps - aio_ineps),
        "fora_autocomplete_com_painel_publico": len(com_painel),
        "fora_autocomplete_sem_painel": len(sem_painel),
        "encontradas_aio_total": len(pdf_ineps & aio_ineps) + len(com_painel),
        "nao_encontradas_aio": sorted(sem_painel),
        "fora_autocomplete_com_painel": sorted(com_painel),
        "fora_autocomplete_lista": sorted(pdf_ineps - aio_ineps),
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "cobertura_pdf_vs_aio.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lista_path = saida / "ineps_pdf_estaduais.txt"
    lista_path.write_text("\n".join(str(i) for i in sorted(pdf_ineps)), encoding="utf-8")
    return relatorio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extrai dados ENEM por escola da AIO (MS).")
    parser.add_argument("--rede", choices=["Federal", "Estadual", "Municipal", "Privada"], help="Filtrar rede.")
    parser.add_argument("--inep", nargs="+", type=int, help="Codigos INEP especificos.")
    parser.add_argument("--inep-list", type=Path, help="Arquivo com um CO_INEP por linha.")
    parser.add_argument("--pdf-estaduais", type=Path, help="PDF com codigos INEP das escolas estaduais MS.")
    parser.add_argument("--comparar-pdf", action="store_true", help="Comparar INEPs do PDF com cobertura AIO e sair.")
    parser.add_argument("--descobrir", action="store_true", help="So descobrir escolas via autocomplete.")
    parser.add_argument("--sem-descobrir", action="store_true", help="Nao usar autocomplete; exige --inep ou --inep-list.")
    parser.add_argument("--cache-descoberta", type=Path, default=SAIDA_PADRAO / "escolas_ms_descobertas.json")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--delay", type=float, default=0.35, help="Intervalo entre requisicoes (s).")
    parser.add_argument("--limite", type=int, default=0, help="Limitar numero de escolas (teste).")
    parser.add_argument("--com-login", action="store_true", help="Usar login AIO para extrair participantes.")
    parser.add_argument("--aio-email", default=None, help="E-mail AIO (ou env AIO_EMAIL).")
    parser.add_argument("--aio-password", default=None, help="Senha AIO (ou env AIO_PASSWORD).")
    parser.add_argument(
        "--aio-session",
        default=None,
        help="Valor do cookie _aio_session copiado do navegador (ou env AIO_SESSION).",
    )
    parser.add_argument("--debug-aio", action="store_true", help="Salvar HTML autenticado de debug em --saida/debug_aio/.")
    parser.add_argument(
        "--completar-participantes-parquet",
        action="store_true",
        help="Apos extracao (ou sozinho), preencher N_PARTICIPANTES via parquet INEP 2024-2025.",
    )
    parser.add_argument("--parquet", type=Path, default=None, help="Parquet INEP para participantes (default enem_config.PARQUET).")
    args = parser.parse_args(argv)

    aio_email = args.aio_email or os.getenv("AIO_EMAIL")
    aio_password = args.aio_password or os.getenv("AIO_PASSWORD")
    aio_session = args.aio_session or os.getenv("AIO_SESSION")

    pdf_path = args.pdf_estaduais or PDF_ESTADUAIS_PADRAO
    if args.completar_participantes_parquet and args.comparar_pdf:
        parser.error("--completar-participantes-parquet nao combina com --comparar-pdf.")

    only_parquet = (
        args.completar_participantes_parquet
        and not args.comparar_pdf
        and not args.descobrir
        and not args.inep
        and not args.inep_list
        and not args.pdf_estaduais
    )
    if only_parquet:
        from aio_participantes_parquet import completar_historico_csv
        from enem_config import PARQUET

        configure_logging(__name__)
        historico_path = args.saida / "enem_escolas_historico.csv"
        if not historico_path.exists():
            parser.error(f"CSV historico nao encontrado: {historico_path}")
        meta = completar_historico_csv(
            csv_path=historico_path,
            parquet=args.parquet or PARQUET,
        )
        logger.info("Participantes parquet: %s linhas preenchidas", meta["linhas_preenchidas"])
        return 0

    if args.comparar_pdf:
        if not pdf_path.exists():
            parser.error(f"PDF nao encontrado: {pdf_path}")
        rel = comparar_pdf_aio(pdf_path, args.saida)
        logger.info(
            "PDF: %s escolas | autocomplete AIO: %s | painel publico extra: %s | total AIO: %s | nao encontradas: %s",
            rel["pdf_total"],
            rel["no_autocomplete_aio"],
            rel["fora_autocomplete_com_painel_publico"],
            rel["encontradas_aio_total"],
            rel["fora_autocomplete_sem_painel"],
        )
        return 0

    use_login = args.com_login or bool(aio_session or (aio_email and aio_password))
    if args.com_login and not aio_session and (not aio_email or not aio_password):
        parser.error(
            "Autenticacao AIO ausente. Use uma das opcoes:\n"
            f"  1) Cookie do navegador: --aio-session ou AIO_SESSION em {ENV_PATH}\n"
            f"  2) E-mail/senha: AIO_EMAIL e AIO_PASSWORD em {ENV_PATH}\n"
            "Copie _aio_session em F12 > Application > Cookies > aio.com.br"
        )
    client = AioClient(
        delay=args.delay,
        session_cookie=aio_session if use_login else None,
        email=aio_email if use_login and not aio_session else None,
        password=aio_password if use_login and not aio_session else None,
    )
    if use_login and not client.authenticated:
        parser.error(
            "Autenticacao AIO falhou. Teste: python diag_aio_login.py "
            "ou use --aio-session com cookie fresco do navegador."
        )

    escolas_map: dict[int, str] = {}

    if args.pdf_estaduais:
        if not pdf_path.exists():
            parser.error(f"PDF nao encontrado: {pdf_path}")
        for inep in extrair_ineps_pdf(pdf_path):
            escolas_map.setdefault(inep, "")
        logger.info("Carregados %s INEPs do PDF %s", len(escolas_map), pdf_path.name)

    if args.inep:
        escolas_map.update({i: "" for i in args.inep})
    if args.inep_list:
        for i in carregar_ineps_arquivo(args.inep_list):
            escolas_map.setdefault(i, "")

    if not args.sem_descobrir and not escolas_map:
        escolas_map = descobrir_escolas_ms(client, cache_path=args.cache_descoberta)

    if args.descobrir:
        logger.info("Descoberta concluida: %s escolas", len(escolas_map))
        return 0

    if not escolas_map:
        parser.error("Informe --inep, --inep-list ou deixe a descoberta automatica habilitada.")

    ineps = sorted(escolas_map)
    if args.limite > 0:
        ineps = ineps[: args.limite]

    linhas: list[dict] = []
    resumo: list[dict] = []
    ok = sem_dados = filtradas = com_participantes = 0

    debug_dir = args.saida / "debug_aio" if args.debug_aio else None

    for idx, co_inep in enumerate(ineps, start=1):
        nome_auto = escolas_map.get(co_inep, "")
        logger.info("[%s/%s] CO_INEP=%s", idx, len(ineps), co_inep)
        try:
            html = client.pagina_escola(co_inep)
            escola = parsear_pagina_escola(html, co_inep, nome_auto)
            if client.authenticated:
                try:
                    escola = enriquecer_com_login(
                        client,
                        escola,
                        debug_dir=debug_dir if args.debug_aio and idx <= 3 else None,
                    )
                except Exception as exc:
                    logger.warning("  %s: historico autenticado indisponivel (%s)", co_inep, exc)
        except Exception as exc:
            logger.error("Erro ao buscar %s: %s", co_inep, exc)
            continue

        if args.rede and escola.rede and escola.rede != args.rede:
            filtradas += 1
            continue
        if args.rede and not escola.rede:
            filtradas += 1
            continue

        if escola.erro:
            sem_dados += 1
            logger.warning("  %s: %s", co_inep, escola.erro)
        else:
            ok += 1
        if escola.participantes_por_ano:
            com_participantes += 1

        linhas.extend(escola_para_linhas(escola))
        resumo.append({
            "CO_INEP": escola.co_inep,
            "NOME_ESCOLA": escola.nome,
            "REDE": escola.rede,
            "MUNICIPIO": escola.municipio,
            "UF": escola.uf,
            "NU_ANO": escola.ano_ultimo,
            "RANKING_MUNICIPIO": escola.ranking_municipio,
            "RANKING_UF": escola.ranking_uf,
            "RANKING_BRASIL": escola.ranking_brasil,
            "ANOS_HISTORICO": len(escola.historico),
            "ANOS_COM_PARTICIPANTES": len(escola.participantes_por_ano),
            "AIO_SCHOOL_ID": escola.aio_school_id,
            "ERRO": escola.erro,
        })

    args.saida.mkdir(parents=True, exist_ok=True)
    historico_path = args.saida / "enem_escolas_historico.csv"
    resumo_path = args.saida / "enem_escolas_resumo.csv"
    salvar_csv(historico_path, linhas)
    salvar_csv(resumo_path, resumo)

    meta = {
        "fonte": "aio.com.br",
        "endpoint_autocomplete": AUTOCOMPLETE_URL,
        "endpoint_escola": ESCOLA_URL,
        "total_consultadas": len(ineps),
        "com_dados": ok,
        "sem_dados": sem_dados,
        "filtradas_rede": filtradas,
        "rede_filtro": args.rede,
        "linhas_historico": len(linhas),
        "login_aio": client.authenticated,
        "escolas_com_participantes": com_participantes,
        "pdf_estaduais": str(pdf_path) if pdf_path.exists() else None,
    }
    meta_path = args.saida / "meta_scrape_aio.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.completar_participantes_parquet:
        from aio_participantes_parquet import completar_historico_csv
        from enem_config import PARQUET

        part_meta = completar_historico_csv(
            csv_path=historico_path,
            parquet=args.parquet or PARQUET,
        )
        meta["participantes_parquet"] = part_meta
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            "Participantes parquet: %s linhas preenchidas (2024-2025)",
            part_meta["linhas_preenchidas"],
        )

    logger.info(
        "Concluido: %s com dados, %s sem dados, %s filtradas por rede. Saida: %s",
        ok,
        sem_dados,
        filtradas,
        args.saida,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
