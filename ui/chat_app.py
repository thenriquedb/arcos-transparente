"""Interface de chat do Arcos Transparente via Chainlit.

Montado pelo FastAPI (``ui/server.py``) em ``/chat`` atraves de
``chainlit.utils.mount_chainlit``. Reutiliza o caso de uso framework-agnostico
``ChatbotApplication.ask`` — todo o "cerebro" continua em ``agents/chatbot``.
"""

from __future__ import annotations

import sys
import threading
import time
from collections import deque
from pathlib import Path

import chainlit as cl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.chatbot import ChatbotAgentBackend, ChatbotApplication, ChatSession  # noqa: E402
from ui.errors import friendly_error_message  # noqa: E402


# --- Limites de abuso (endpoint publico que dispara chamadas pagas ao LLM) -----
# Tamanho maximo da pergunta (evita prompts gigantes e custo descontrolado).
MAX_MESSAGE_CHARS = 2000
# Janela deslizante para rate limit.
RATE_WINDOW_SECONDS = 60.0
# Maximo de mensagens por sessao na janela.
MAX_MESSAGES_PER_SESSION = 30
# Disjuntor global do processo (protege custo mesmo com muitas sessoes).
MAX_MESSAGES_GLOBAL = 120
# Maximo de mensagens mantidas no historico da sessao (memoria + custo de tokens).
MAX_HISTORY_MESSAGES = 30

# Estruturas tocadas apenas em on_message (event loop, single-thread) -> sem race.
_session_hits: dict[str, deque[float]] = {}
_global_hits: deque[float] = deque()


def _prune(hits: deque[float], now: float) -> None:
    cutoff = now - RATE_WINDOW_SECONDS
    while hits and hits[0] < cutoff:
        hits.popleft()


def _rate_limited(session_id: str) -> bool:
    """Registra um hit e devolve True se o limite (sessao ou global) estourou."""

    now = time.monotonic()
    session_hits = _session_hits.setdefault(session_id, deque())
    _prune(session_hits, now)
    _prune(_global_hits, now)

    if len(session_hits) >= MAX_MESSAGES_PER_SESSION or len(_global_hits) >= MAX_MESSAGES_GLOBAL:
        return True

    session_hits.append(now)
    _global_hits.append(now)
    return False


# Backend unico por processo: sem estado entre sessoes (cacheia agentes por
# subconjunto de tools internamente, com lock proprio). As sessoes ficam
# isoladas pelo ChatSession (session_id como thread do agente).
_BACKEND: ChatbotAgentBackend | None = None
_BACKEND_LOCK = threading.Lock()


def _get_backend() -> ChatbotAgentBackend:
    global _BACKEND
    if _BACKEND is None:
        with _BACKEND_LOCK:
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
            label="Servidores e salários",
            message="Qual foi o salário do prefeito em 2025?",
            icon=icon,
        ),
        cl.Starter(
            label="Gasto do festival gastronômico",
            message="Qual foi o gasto do festival gastronômico em 2025?",
            icon=icon,
        ),
        cl.Starter(
            label="Telefone de uma secretaria",
            message="Qual é o telefone da Secretaria de Saúde?",
            icon=icon,
        ),
    ]


def _build_application() -> ChatbotApplication:
    return ChatbotApplication(
        backend=_get_backend(),
        session=ChatSession(id=cl.context.session.id),
    )


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("app", _build_application())


@cl.on_message
async def on_message(message: cl.Message) -> None:
    content = (message.content or "").strip()

    if not content:
        await cl.Message(content="Envie uma pergunta para eu poder ajudar.").send()
        return

    if len(content) > MAX_MESSAGE_CHARS:
        await cl.Message(
            content=(
                f"Sua pergunta é muito longa (limite de {MAX_MESSAGE_CHARS} caracteres). Resuma e tente novamente."
            )
        ).send()
        return

    if _rate_limited(cl.context.session.id):
        await cl.Message(
            content=("Você enviou muitas perguntas em pouco tempo. Aguarde alguns instantes e tente novamente.")
        ).send()
        return

    app: ChatbotApplication = cl.user_session.get("app")
    if app is None:
        app = _build_application()
        cl.user_session.set("app", app)

    try:
        response = await cl.make_async(app.ask)(content)
        await cl.Message(content=response.content).send()
    except Exception as exc:  # noqa: BLE001
        # Nunca expõe a exceção crua ao usuário; friendly_error_message cobre os
        # casos conhecidos (config/provider/banco) e um fallback generico.
        await cl.Message(content=friendly_error_message(exc)).send()
    finally:
        _trim_history(app)


def _trim_history(app: ChatbotApplication) -> None:
    history = getattr(getattr(app, "session", None), "history", None)
    if history is not None and len(history) > MAX_HISTORY_MESSAGES:
        del history[:-MAX_HISTORY_MESSAGES]
