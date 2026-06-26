from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import ui.chat_app as chat_app
from agents.chatbot import ChatResponse


class FakeUserSession:
    def __init__(self, app) -> None:
        self._app = app

    def get(self, key: str):
        return self._app if key == "app" else None

    def set(self, key: str, value) -> None:  # noqa: D401 - no-op para o teste
        pass


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    chat_app._session_hits.clear()
    chat_app._global_hits.clear()
    yield
    chat_app._session_hits.clear()
    chat_app._global_hits.clear()


def _install_fakes(monkeypatch, app, session_id: str = "sess-1") -> list[str]:
    sent: list[str] = []

    class FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

        async def send(self) -> None:
            sent.append(self.content)

    def fake_make_async(fn):
        async def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(chat_app.cl, "user_session", FakeUserSession(app))
    monkeypatch.setattr(chat_app.cl, "Message", FakeMessage)
    monkeypatch.setattr(chat_app.cl, "make_async", fake_make_async)
    monkeypatch.setattr(
        chat_app.cl,
        "context",
        SimpleNamespace(session=SimpleNamespace(id=session_id)),
    )
    return sent


def test_on_message_envia_resposta_final(monkeypatch) -> None:
    app = SimpleNamespace(ask=lambda q: ChatResponse(content="Resposta final."))
    sent = _install_fakes(monkeypatch, app)

    asyncio.run(chat_app.on_message(SimpleNamespace(content="quem é o prefeito?")))

    assert sent == ["Resposta final."]


def test_on_message_excecao_usa_mensagem_amigavel(monkeypatch) -> None:
    def ask(_q):
        raise RuntimeError("no such table: servidores")

    sent = _install_fakes(monkeypatch, SimpleNamespace(ask=ask))

    asyncio.run(chat_app.on_message(SimpleNamespace(content="quantos servidores?")))

    assert len(sent) == 1
    assert "Banco local indisponivel" in sent[0]


def test_on_message_value_error_de_config_nao_vaza(monkeypatch) -> None:
    # ValueError de bootstrap (ex.: env faltando) deve passar pelo
    # friendly_error_message, nao ser exposto cru ao usuario.
    def ask(_q):
        raise ValueError("OPENAI_API_KEY deve ser informado no ambiente ou no .env.")

    sent = _install_fakes(monkeypatch, SimpleNamespace(ask=ask))

    asyncio.run(chat_app.on_message(SimpleNamespace(content="oi")))

    assert sent == [
        "Configuracao do chatbot incompleta. Defina LLM_PROVIDER=openai, "
        "OPENAI_MODEL e OPENAI_API_KEY no ambiente ou no .env antes de iniciar o chat."
    ]
    assert "OPENAI_API_KEY deve ser informado" not in sent[0]


def test_on_message_pergunta_vazia(monkeypatch) -> None:
    called = []
    app = SimpleNamespace(ask=lambda q: called.append(q) or ChatResponse(content="x"))
    sent = _install_fakes(monkeypatch, app)

    asyncio.run(chat_app.on_message(SimpleNamespace(content="   ")))

    assert called == []  # nao chama o LLM
    assert "Envie uma pergunta" in sent[0]


def test_on_message_mensagem_muito_longa(monkeypatch) -> None:
    called = []
    app = SimpleNamespace(ask=lambda q: called.append(q) or ChatResponse(content="x"))
    sent = _install_fakes(monkeypatch, app)

    longa = "a" * (chat_app.MAX_MESSAGE_CHARS + 1)
    asyncio.run(chat_app.on_message(SimpleNamespace(content=longa)))

    assert called == []  # nao chama o LLM
    assert "muito longa" in sent[0]


def test_on_message_rate_limit_por_sessao(monkeypatch) -> None:
    app = SimpleNamespace(ask=lambda q: ChatResponse(content="ok"))
    sent = _install_fakes(monkeypatch, app, session_id="flood")

    limite = chat_app.MAX_MESSAGES_PER_SESSION
    for _ in range(limite):
        asyncio.run(chat_app.on_message(SimpleNamespace(content="pergunta")))
    # A proxima excede o limite da janela.
    asyncio.run(chat_app.on_message(SimpleNamespace(content="pergunta")))

    assert sent.count("ok") == limite
    assert "muitas perguntas" in sent[-1]
