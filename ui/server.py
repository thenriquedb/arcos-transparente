"""App web do Arcos Transparente: landing (FastAPI + Jinja2) + chat (Chainlit).

Surface unica em Python: o FastAPI serve a landing institucional em ``/`` e o
Chainlit (UI de chat) e montado em ``/chat`` via ``mount_chainlit``. Rodar com:

    uv run uvicorn ui.server:app --port 8501

Todo o "cerebro" continua em ``agents/chatbot`` — esta camada so apresenta.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from chainlit.config import config as _chainlit_config
from chainlit.utils import mount_chainlit
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


UI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = UI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CHAT_PATH = "/chat"
GITHUB_LINK = "https://github.com/thenriquedb/arcos-transparente"
DATA_RANGE = "Janeiro de 2025 – Maio de 2026"
# URL publica canonica. Se nao definida, cai para a origem da propria requisicao
# (evita apontar canonical/OG/sitemap para um dominio errado no deploy).
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
# Origens permitidas no CORS do chat (Chainlit). Same-origin NAO depende disto;
# por padrao bloqueia cross-origin. Ex.: ALLOWED_ORIGINS="https://a.gov,https://b".
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
PAGE_TITLE = "Arcos Transparente — Consulte os dados públicos de Arcos (MG)"
PAGE_DESCRIPTION = (
    "Ferramenta gratuita para consultar contratos, salários e licitações da prefeitura de Arcos em linguagem natural."
)

# Conteudo da landing (portado dos componentes Next).
PROBLEM_QUESTIONS = [
    "Quanto foi gasto com diárias em 2025?",
    "Quem ganhou determinada licitação?",
    "Quais contratos estão ativos?",
    "Quanto a prefeitura recebeu em transferências?",
    "Qual o telefone de uma secretaria?",
    "Quais são os horários de ônibus?",
]

STEPS = [
    {
        "icon": "message-square",
        "title": "Você pergunta",
        "body": "Digite sua dúvida do jeito que falaria no dia a dia.",
    },
    {
        "icon": "search",
        "title": "O sistema procura",
        "body": "Ele busca a informação nos dados públicos disponíveis.",
    },
    {
        "icon": "file-text",
        "title": "Você confere a resposta",
        "body": "A resposta vem com a fonte, o período consultado e os dados encontrados.",
    },
]

CATEGORIES = [
    {
        "icon": "banknote",
        "title": "Dinheiro público",
        "themes": ["Gastos", "Receitas", "Contratos", "Licitações"],
        "questions": [
            "Quanto a prefeitura gastou com saúde em 2025?",
            "Quais foram os maiores contratos do ano?",
            "Quais empresas mais receberam dinheiro da prefeitura?",
            "Quanto a prefeitura arrecadou em 2025?",
        ],
    },
    {
        "icon": "users",
        "title": "Servidores e salários",
        "themes": ["Salários", "Servidores", "Câmara", "Prefeitura"],
        "questions": [
            "Qual foi o salário do prefeito em março de 2025?",
            "Quais são os maiores salários do município?",
            "Quais foram os maiores pagamentos de diárias do ano?",
            "Quais são os cargos e salários da Câmara?",
        ],
    },
    {
        "icon": "truck",
        "title": "Bens, frota e operação",
        "themes": ["Frota", "Patrimônio", "Almoxarifado", "Diárias"],
        "questions": [
            "Quais são os veículos da frota da prefeitura?",
            "Quanto foi gasto com diárias em 2025?",
            "Quais bens a prefeitura tem registrados?",
            "Quais são os materiais com maior quantidade em estoque?",
        ],
    },
    {
        "icon": "bus",
        "title": "Serviços e cidade",
        "themes": ["Telefones úteis", "Ônibus", "Secretarias"],
        "questions": [
            "Qual é o telefone da Secretaria de Saúde?",
            "Quais são os horários de ônibus?",
            "Como funciona a tarifa zero?",
            "Onde encontro os contatos da prefeitura?",
        ],
    },
]

templates = Jinja2Templates(directory=str(UI_DIR / "templates"))

# Cabecalhos de seguranca. A CSP so e aplicada fora do /chat: a SPA do Chainlit
# usa scripts inline / eval / websockets proprios e quebraria sob uma CSP estrita.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
    "img-src 'self' data:; script-src 'self'; connect-src 'self'; form-action 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com"
)


def _base_url(request: Request) -> str:
    return PUBLIC_BASE_URL or str(request.base_url).rstrip("/")


app = FastAPI(title="Arcos Transparente")
app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    if not request.url.path.startswith(CHAT_PATH):
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    return response


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> Response:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "chat_url": CHAT_PATH,
            "github_link": GITHUB_LINK,
            "data_range": DATA_RANGE,
            "production_url": _base_url(request),
            "page_title": PAGE_TITLE,
            "page_description": PAGE_DESCRIPTION,
            "problem_questions": PROBLEM_QUESTIONS,
            "steps": STEPS,
            "categories": CATEGORIES,
        },
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots(request: Request) -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {_base_url(request)}/sitemap.xml\n"


@app.get("/sitemap.xml")
async def sitemap(request: Request) -> Response:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{_base_url(request)}/</loc><changefreq>weekly</changefreq>"
        "<priority>1.0</priority></url>\n"
        "</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")


# Restringe o CORS do Chainlit antes de montar (default: sem cross-origin).
# Precisa ocorrer antes de mount_chainlit, que constroi o CORSMiddleware do chat.
_chainlit_config.project.allow_origins = ALLOWED_ORIGINS

mount_chainlit(app=app, target=str(UI_DIR / "chat_app.py"), path=CHAT_PATH)
