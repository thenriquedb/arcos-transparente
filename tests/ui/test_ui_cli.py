from __future__ import annotations

from agents.chatbot import ChatbotApplication, ChatResponse, ChatSession
from ui.cli import run_interactive, run_once


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def answer(self, question: str, session_id: str) -> ChatResponse:
        self.calls.append((question, session_id))
        return ChatResponse(content=f"resposta para: {question}")


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
