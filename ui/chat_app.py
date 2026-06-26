"""Interface de chat do Arcos Transparente via Chainlit.

Montado pelo FastAPI (``ui/server.py``) em ``/chat`` atraves de
``chainlit.utils.mount_chainlit``. Reutiliza o caso de uso framework-agnostico
``ChatbotApplication.ask`` — todo o "cerebro" continua em ``agents/chatbot``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import chainlit as cl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.chatbot import ChatbotAgentBackend, ChatbotApplication, ChatSession  # noqa: E402
from ui.errors import friendly_error_message  # noqa: E402


# Backend unico por processo: sem estado entre sessoes (cacheia agentes por
# subconjunto de tools internamente). As sessoes ficam isoladas pelo ChatSession.
_BACKEND: ChatbotAgentBackend | None = None


def _get_backend() -> ChatbotAgentBackend:
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = ChatbotAgentBackend()
    return _BACKEND


@cl.data_layer
def _no_persistence():
    """Desliga a camada de dados do Chainlit.

    Sem isto, o Chainlit sequestra a env ``DATABASE_URL`` (que o app usa para o
    SQLite proprio) e tenta inicializar a propria camada de persistencia de chat,
    quebrando em ``/chat/project/settings``. Esta POC nao precisa persistir o
    historico — retornar ``None`` mantem o Chainlit sem data layer.
    """

    return None


@cl.set_starters
async def starters(user=None):
    _ = user
    icon = "/public/favicon.svg"
    return [
        cl.Starter(
            label="Gastos com saúde em 2025",
            message="Quanto a prefeitura gastou com saúde em 2025?",
            icon=icon,
        ),
        cl.Starter(
            label="Salário do prefeito",
            message="Qual foi o salário do prefeito em março de 2025?",
            icon=icon,
        ),
        cl.Starter(
            label="Maiores contratos do ano",
            message="Quais foram os maiores contratos do ano?",
            icon=icon,
        ),
        cl.Starter(
            label="Telefone de uma secretaria",
            message="Qual é o telefone da Secretaria de Saúde?",
            icon=icon,
        ),
    ]


@cl.on_chat_start
async def on_chat_start() -> None:
    app = ChatbotApplication(
        backend=_get_backend(),
        session=ChatSession(id=cl.context.session.id),
    )
    cl.user_session.set("app", app)


@cl.on_message
async def on_message(message: cl.Message) -> None:
    app: ChatbotApplication = cl.user_session.get("app")
    if app is None:
        app = ChatbotApplication(
            backend=_get_backend(),
            session=ChatSession(id=cl.context.session.id),
        )
        cl.user_session.set("app", app)

    try:
        response = await cl.make_async(app.ask)(message.content)
        await cl.Message(content=response.content).send()
    except ValueError as exc:
        # Guardrail / pergunta vazia: a propria mensagem ja e amigavel.
        await cl.Message(content=str(exc)).send()
    except Exception as exc:  # noqa: BLE001
        await cl.Message(content=friendly_error_message(exc)).send()
