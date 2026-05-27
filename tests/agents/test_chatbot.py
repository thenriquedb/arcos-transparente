from __future__ import annotations

import pytest

from agents.chatbot.cli import run_interactive, run_once
from agents.chatbot.core import ChatResponse, ChatSession, ChatbotApplication


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def answer(self, question: str, session_id: str) -> ChatResponse:
        self.calls.append((question, session_id))
        return ChatResponse(content=f"resposta para: {question}")


def test_chatbot_application_mantem_estado_da_sessao() -> None:
    backend = FakeBackend()
    app = ChatbotApplication(
        backend=backend,
        session=ChatSession(id="sessao-teste"),
    )

    response = app.ask("  Quais contratos da educacao?  ")

    assert response.content == "resposta para: Quais contratos da educacao?"
    assert backend.calls == [("Quais contratos da educacao?", "sessao-teste")]
    assert [(msg.role, msg.content) for msg in app.session.history] == [
        ("user", "Quais contratos da educacao?"),
        ("assistant", "resposta para: Quais contratos da educacao?"),
    ]


def test_chatbot_application_rejeita_pergunta_vazia() -> None:
    app = ChatbotApplication(backend=FakeBackend())

    with pytest.raises(ValueError) as exc_info:
        app.ask("   ")

    assert "pergunta nao pode ser vazia" in str(exc_info.value)


def test_chatbot_application_responde_identidade_sem_chamar_backend() -> None:
    backend = FakeBackend()
    app = ChatbotApplication(backend=backend)

    response = app.ask("quem é você?")

    assert "assistente do projeto Arcos Transparente" in response.content
    assert response.metadata == {"local_response": "identity"}
    assert backend.calls == []


def test_cli_run_once_imprime_resposta() -> None:
    output: list[str] = []
    app = ChatbotApplication(
        backend=FakeBackend(),
        session=ChatSession(id="cli-test"),
    )

    exit_code = run_once(app, "Quanto foi contratado?", output.append)

    assert exit_code == 0
    assert output == ["resposta para: Quanto foi contratado?"]


def test_cli_interativo_encerra_com_sair() -> None:
    output: list[str] = []
    inputs = iter(["sair"])

    exit_code = run_interactive(
        ChatbotApplication(backend=FakeBackend()),
        input_func=lambda _prompt: next(inputs),
        output=output.append,
    )

    assert exit_code == 0
    assert output[-1] == "Encerrando chat."
