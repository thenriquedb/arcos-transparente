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
PRIVACY_PATH = "/privacidade"
COVERAGE_PATH = "/cobertura"
GITHUB_LINK = "https://github.com/thenriquedb/arcos-transparente"
DATA_RANGE = os.getenv("DATA_RANGE", "Janeiro de 2025 a Maio de 2026")
# Responsavel/operador e contato (LGPD). Configure no deploy. Se vazio, o contato
# aponta para as Issues do repositorio.
OPERATOR_NAME = os.getenv("OPERATOR_NAME", "").strip()
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()
# Fonte oficial dos dados, exibida na secao de credibilidade (link opcional).
SOURCE_NAME = os.getenv("SOURCE_NAME", "Portal da Transparência da Prefeitura de Arcos (MG)")
SOURCE_URL = os.getenv("SOURCE_URL", "").strip()
OG_IMAGE_PATH = "/static/og-image.svg"
# URL publica canonica. Se nao definida, cai para a origem da propria requisicao
# (evita apontar canonical/OG/sitemap para um dominio errado no deploy).
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
# Origens permitidas no CORS do chat (Chainlit). Same-origin NAO depende disto;
# por padrao bloqueia cross-origin. Ex.: ALLOWED_ORIGINS="https://a.gov,https://b".
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
PAGE_TITLE = "Arcos Transparente — Consulte os dados públicos de Arcos (MG)"
PAGE_DESCRIPTION = (
    "Pergunte em português sobre gastos, salários, contratos e diárias da prefeitura de Arcos (MG). "
)

# Tela de boas-vindas do chat (Chainlit le chainlit_pt-BR.md / chainlit.md).
# Gerada a partir de DATA_RANGE para manter o periodo em sincronia com a landing
# e a pagina de privacidade (fonte unica de verdade).
WELCOME_MD = """# Arcos Transparente

Pergunte em **português** sobre as contas públicas de Arcos (MG) — gastos, salários,
contratos, diárias, frota e serviços da cidade. Sempre que possível, a resposta traz o
**período** e a **fonte** para você conferir.

👉 Clique em um exemplo abaixo ou escreva sua pergunta.

---

**Antes de usar as respostas:**

- 🤖 São geradas por **IA** e podem conter erros ou estar incompletas — **confira na fonte oficial**.
- 🗓️ Período coberto pelos dados: **{data_range}**.
- 🏛️ Baseadas em **dados públicos oficiais**. Projeto **independente**, sem vínculo com a prefeitura; não substitui os canais oficiais.
- 🔒 Sua pergunta é processada por um provedor de IA para gerar a resposta. Veja a [Política de Privacidade](/privacidade).

[Sobre o projeto e fontes](/) · [Privacidade](/privacidade)
"""


def _write_chat_welcome() -> None:
    """Gera as telas de boas-vindas do Chainlit a partir de DATA_RANGE.

    Mantem o periodo dos dados consistente entre landing, privacidade e chat.
    Escrito antes de mount_chainlit; o Chainlit le esses arquivos por requisicao.
    """

    content = WELCOME_MD.format(data_range=DATA_RANGE)
    root = Path(getattr(_chainlit_config, "root", None) or PROJECT_ROOT)
    for name in ("chainlit_pt-BR.md", "chainlit.md"):
        try:
            (root / name).write_text(content, encoding="utf-8")
        except OSError:
            # Filesystem somente-leitura: mantem o arquivo versionado como fallback.
            pass


# Comparativo honesto com o portal oficial (diferencial).
COMPARISON = {
    "portal": [
        "Vários sistemas, planilhas e relatórios separados",
        "Termos técnicos de orçamento público",
        "Você precisa procurar e cruzar os dados",
    ],
    "here": [
        "Uma pergunta em português, uma resposta direta",
        "Sempre que possível, com período e fonte para conferir",
        "Grátis, sem cadastro e sem instalar nada",
    ],
}

STEPS = [
    {
        "icon": "message-square",
        "title": "Você pergunta",
        "body": "Escreva sua dúvida do jeito que falaria no dia a dia.",
    },
    {
        "icon": "search",
        "title": "Consultamos os dados públicos",
        "body": "A pergunta é respondida com base nos dados oficiais já reunidos.",
    },
    {
        "icon": "file-text",
        "title": "Você confere na fonte",
        "body": "Sempre que possível, a resposta traz o período e a origem do dado para você validar.",
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
            "Quanto a prefeitura recebeu de emendas parlamentares?",
            "Quanto a prefeitura arrecadou em 2025?",
        ],
    },
    {
        "icon": "users",
        "title": "Servidores e salários",
        "themes": ["Salários", "Servidores", "Câmara", "Prefeitura"],
        "questions": [
            "Quais são os maiores salários do município?",
            "Qual é o salário do prefeito?",
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
        "themes": ["Telefones úteis", "Secretarias", "Contatos"],
        "questions": [
            "Qual é o telefone da Secretaria de Saúde?",
            "Quais secretarias existem na prefeitura?",
            "Onde encontro os contatos da prefeitura?",
            "Quais são os horários de ônibus?",
        ],
    },
]

# Cobertura do agente para a pagina de documentacao (/cobertura).
# Fiel a agents/tools/names.py + corpus RAG em data/rag. Cada categoria responde:
# o que e, o que da para perguntar, quais dados sao usados e limitacoes proprias.
# Data opcional da ultima atualizacao da base (ex.: "junho de 2026"). Sem valor,
# a pagina nao mostra o badge (evita inventar data).
DATA_UPDATED_AT = os.getenv("DATA_UPDATED_AT", "").strip()

COVERAGE_SECTIONS = [
    {
        "id": "financeiros",
        "icon": "wallet",
        "title": "Dinheiro público",
        "description": "Para onde vai e de onde vem o dinheiro do município.",
        "categories": [
            {
                "icon": "banknote",
                "title": "Gastos e despesas",
                "what": "Tudo o que a prefeitura pagou, por período, por área e por fornecedor.",
                "ask": [
                    "Quanto foi gasto com saúde em 2025?",
                    "Quais foram as maiores despesas do ano?",
                    "Quanto a prefeitura gastou com a frota?",
                ],
                "datasets": [
                    "Despesas orçamentárias",
                    "Despesas por função (saúde, educação, etc.)",
                    "Despesas por veículo da frota",
                ],
            },
            {
                "icon": "trending-up",
                "title": "Receitas e arrecadação",
                "what": "De onde vem o dinheiro do município e quanto entrou.",
                "ask": [
                    "Quanto a prefeitura arrecadou em 2025?",
                    "Quais são as maiores fontes de receita?",
                ],
                "datasets": ["Receitas arrecadadas por período e por fonte"],
            },
            {
                "icon": "gavel",
                "title": "Contratos e licitações",
                "what": "As contratações e compras públicas: com quem, para quê e por quanto.",
                "ask": [
                    "Quais foram os maiores contratos do ano?",
                    "O que foi comprado em um contrato?",
                    "Quais licitações aconteceram em 2025?",
                ],
                "datasets": [
                    "Contratos (valor, fornecedor, objeto, vigência)",
                    "Itens adquiridos em contratos",
                    "Licitações",
                ],
            },
            {
                "icon": "arrow-left-right",
                "title": "Transferências e emendas",
                "what": "Recursos que o município recebeu de outros entes, como emendas parlamentares.",
                "ask": [
                    "Quanto a prefeitura recebeu de emendas parlamentares?",
                    "Quais transferências o município recebeu?",
                ],
                "datasets": ["Transferências financeiras", "Emendas parlamentares"],
            },
            {
                "icon": "target",
                "title": "Planejamento e orçamento",
                "what": "O que estava previsto no orçamento: programas, ações e valores planejados.",
                "ask": [
                    "Quais programas estão previstos no orçamento?",
                    "Quanto foi planejado para a saúde?",
                ],
                "datasets": ["Planejamento orçamentário (programas, ações e valores)"],
                "limit": "Mostra o que foi planejado. Para o que foi realmente gasto, veja Gastos e despesas.",
            },
        ],
    },
    {
        "id": "pessoas",
        "icon": "users",
        "title": "Pessoas e remuneração",
        "description": "Quem trabalha para o município e quanto recebe.",
        "categories": [
            {
                "icon": "users",
                "title": "Servidores e folha",
                "what": "Quem trabalha na prefeitura, em que cargo, onde e quanto recebe.",
                "ask": [
                    "Quais são os maiores salários do município?",
                    "Qual é a folha de pagamento por secretaria?",
                    "Qual o histórico de pagamentos de um servidor?",
                ],
                "datasets": [
                    "Servidores e remuneração",
                    "Folha por cargo e por lotação (secretaria)",
                    "Quadro de pessoal",
                    "Histórico funcional e de pagamentos",
                ],
            },
            {
                "icon": "plane",
                "title": "Diárias e passagens",
                "what": "Pagamentos de deslocamento a servidores e agentes públicos.",
                "ask": [
                    "Quanto foi gasto com diárias em 2025?",
                    "Quem recebeu diárias?",
                    "Quais foram os maiores pagamentos de diárias?",
                ],
                "datasets": ["Diárias", "Passagens"],
            },
            {
                "icon": "landmark",
                "title": "Câmara Municipal",
                "what": "Dados do Poder Legislativo: servidores, salários e vereadores.",
                "ask": [
                    "Quais são os cargos e salários da Câmara?",
                    "Quem são os vereadores?",
                    "O que faz a Câmara?",
                ],
                "datasets": [
                    "Servidores e salários da Câmara",
                    "Vereadores e papel da Câmara (acervo)",
                ],
            },
        ],
    },
    {
        "id": "patrimonio",
        "icon": "package",
        "title": "Patrimônio e operação",
        "description": "O que o município possui e como se mantém.",
        "categories": [
            {
                "icon": "truck",
                "title": "Frota",
                "what": "Os veículos do município e quanto custam para manter.",
                "ask": [
                    "Quais veículos a prefeitura tem?",
                    "Quais veículos mais gastam com manutenção?",
                ],
                "datasets": ["Frota municipal", "Custos por veículo"],
            },
            {
                "icon": "package",
                "title": "Bens, patrimônio e almoxarifado",
                "what": "O que a prefeitura possui e o que entra e sai do almoxarifado.",
                "ask": [
                    "Quais bens a prefeitura tem registrados?",
                    "O que há no estoque do almoxarifado?",
                    "Quais foram as movimentações do estoque?",
                ],
                "datasets": [
                    "Bens patrimoniais",
                    "Estoques do almoxarifado",
                    "Movimentações de estoque",
                ],
            },
        ],
    },
    {
        "id": "cidade",
        "icon": "building-2",
        "title": "Cidade e representação",
        "description": "Serviços ao cidadão e quem foi eleito para governar.",
        "categories": [
            {
                "icon": "phone",
                "title": "Serviços ao cidadão",
                "what": "Informações úteis do dia a dia, de um acervo selecionado.",
                "ask": [
                    "Qual é o telefone da Secretaria de Saúde?",
                    "Quais são os horários de ônibus?",
                    "Quais secretarias existem na prefeitura?",
                ],
                "datasets": [
                    "Telefones úteis e contatos",
                    "Estrutura organizacional da prefeitura",
                    "Horários de ônibus e tarifa zero",
                    "Serviços e medicamentos da saúde",
                    "Perguntas frequentes",
                ],
                "limit": "É um acervo curado; não cobre todos os serviços da cidade.",
            },
            {
                "icon": "vote",
                "title": "Eleições e representantes",
                "what": "Quem foi eleito para governar o município.",
                "ask": [
                    "Quem foram os prefeitos eleitos?",
                    "Quem foram os vereadores eleitos?",
                ],
                "datasets": ["Prefeitos e vereadores eleitos"],
            },
        ],
    },
]

# O que a aplicacao ainda NAO cobre (reduz expectativa; aumenta confianca).
NOT_AVAILABLE = [
    "Documentos originais, como notas fiscais, empenhos e editais em PDF",
    "Acompanhamento de obras e sua execução física",
    "Dados em tempo real ou do dia de hoje",
    "Comparações com outras cidades",
    "Períodos fora da base disponível",
    "Ouvidoria, protocolos e pedidos de acesso à informação",
]

FAQ = [
    {
        "q": "Os dados são oficiais?",
        "a": "Sim. Vêm de fontes públicas oficiais do município e não são inventados pela aplicação.",
    },
    {
        "q": "A IA inventa respostas?",
        "a": (
            "Ela responde com base nos dados já carregados. Ainda assim, como toda IA, pode errar ou "
            "interpretar mal — por isso indica a fonte e o período, para você conferir. Quando não "
            "encontra a informação, deve avisar em vez de inventar."
        ),
    },
    {
        "q": "A aplicação altera alguma informação?",
        "a": "Não. É somente leitura: nunca modifica, apaga ou insere dados nos sistemas públicos.",
    },
    {
        "q": "Qual o período coberto?",
        "a": "A base atual cobre {data_range}.",
    },
    {
        "q": "Os dados são atualizados automaticamente?",
        "a": (
            "Não em tempo real. São atualizados quando a base é reimportada das fontes oficiais, "
            "de tempos em tempos."
        ),
    },
    {
        "q": "Posso usar essas respostas como documento oficial?",
        "a": (
            "Não. Elas servem para orientar e facilitar o acesso à informação. Para fins oficiais, "
            "use os documentos e canais oficiais da prefeitura e da Câmara."
        ),
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


def _shared_context(request: Request) -> dict:
    """Variaveis comuns a todas as paginas (header/footer, identidade, LGPD)."""

    base = _base_url(request)
    return {
        "chat_url": CHAT_PATH,
        "privacy_url": PRIVACY_PATH,
        "coverage_url": COVERAGE_PATH,
        "github_link": GITHUB_LINK,
        "operator_name": OPERATOR_NAME,
        "contact_email": CONTACT_EMAIL,
        "production_url": base,
        "og_image": f"{base}{OG_IMAGE_PATH}",
    }


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
            **_shared_context(request),
            "data_range": DATA_RANGE,
            "page_title": PAGE_TITLE,
            "page_description": PAGE_DESCRIPTION,
            "comparison": COMPARISON,
            "steps": STEPS,
            "categories": CATEGORIES,
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
        },
    )


@app.get(COVERAGE_PATH, response_class=HTMLResponse)
async def coverage(request: Request) -> Response:
    n_categorias = sum(len(section["categories"]) for section in COVERAGE_SECTIONS)
    faq = [{"q": item["q"], "a": item["a"].format(data_range=DATA_RANGE)} for item in FAQ]
    return templates.TemplateResponse(
        request,
        "cobertura.html",
        {
            **_shared_context(request),
            "data_range": DATA_RANGE,
            "data_updated_at": DATA_UPDATED_AT,
            "page_title": "O que você pode perguntar — Arcos Transparente",
            "page_description": (
                "A cobertura da base do Arcos Transparente (MG): quais dados públicos a IA consulta, "
                "de onde vêm, até que período e quais são as limitações."
            ),
            "sections": COVERAGE_SECTIONS,
            "not_available": NOT_AVAILABLE,
            "faq": faq,
            "n_categorias": n_categorias,
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
        },
    )


@app.get(PRIVACY_PATH, response_class=HTMLResponse)
async def privacy(request: Request) -> Response:
    return templates.TemplateResponse(
        request,
        "privacidade.html",
        {
            **_shared_context(request),
            "data_range": DATA_RANGE,
            "page_title": "Privacidade — Arcos Transparente",
            "page_description": "Como o Arcos Transparente trata as suas perguntas e os dados públicos consultados.",
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
        },
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots(request: Request) -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {_base_url(request)}/sitemap.xml\n"


@app.get("/sitemap.xml")
async def sitemap(request: Request) -> Response:
    base = _base_url(request)
    pages = [("/", "1.0"), (COVERAGE_PATH, "0.8"), (PRIVACY_PATH, "0.3")]
    urls = "".join(
        f"  <url><loc>{base}{path}</loc><changefreq>weekly</changefreq>"
        f"<priority>{prio}</priority></url>\n"
        for path, prio in pages
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")


# Gera o welcome do chat com o DATA_RANGE atual (fonte unica de verdade).
_write_chat_welcome()

# Restringe o CORS do Chainlit antes de montar (default: sem cross-origin).
# Precisa ocorrer antes de mount_chainlit, que constroi o CORSMiddleware do chat.
_chainlit_config.project.allow_origins = ALLOWED_ORIGINS

mount_chainlit(app=app, target=str(UI_DIR / "chat_app.py"), path=CHAT_PATH)
