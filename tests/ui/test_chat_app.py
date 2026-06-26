from __future__ import annotations

import asyncio
from types import SimpleNamespace

import ui.chat_app as chat_app
from agents.chatbot import ChatResponse


class FakeUserSession:
    def __init__(self, app) -> None:
        self._app = app

    def get(self, key: str):
        return self._app if key == "app" else None

    def set(self, key: str, value) -> None:  # noqa: D401 - no-op para o teste
        pass


def _install_fakes(monkeypatch, app) -> list[str]:
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
    return sent


def test_on_message_envia_resposta_final(monkeypatch) -> None:
    app = SimpleNamespace(ask=lambda q: ChatResponse(content="Resposta final."))
    sent = _install_fakes(monkeypatch, app)

    asyncio.run(chat_app.on_message(SimpleNamespace(content="quem é o prefeito?")))

    assert sent == ["Resposta final."]


def test_on_message_value_error_usa_mensagem_do_guardrail(monkeypatch) -> None:
    def ask(_q):
        raise ValueError("Pergunta fora do escopo do projeto.")

    sent = _install_fakes(monkeypatch, SimpleNamespace(ask=ask))

    asyncio.run(chat_app.on_message(SimpleNamespace(content="qualquer coisa")))

    assert sent == ["Pergunta fora do escopo do projeto."]


def test_on_message_excecao_generica_usa_mensagem_amigavel(monkeypatch) -> None:
    def ask(_q):
        raise RuntimeError("no such table: servidores")

    sent = _install_fakes(monkeypatch, SimpleNamespace(ask=ask))

    asyncio.run(chat_app.on_message(SimpleNamespace(content="quantos servidores?")))

    assert len(sent) == 1
    assert "Banco local indisponivel" in sent[0]
