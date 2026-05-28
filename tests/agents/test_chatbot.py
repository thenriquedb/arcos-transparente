from __future__ import annotations

import pytest

import agents.chatbot.agent as chatbot_agent
from agents.chatbot.cli import run_interactive, run_once
from agents.chatbot.core import (
    ChatbotAgentBackend,
    ChatResponse,
    ChatSession,
    ChatbotApplication,
)


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def answer(self, question: str, session_id: str) -> ChatResponse:
        self.calls.append((question, session_id))
        return ChatResponse(content=f"resposta para: {question}")


def _tool_name(tool_obj) -> str:
    return getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))


def test_criar_agente_chatbot_usa_configuracao_do_modulo(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    def fake_create_agent(*, tools, model, system_prompt, checkpointer=None):
        capturado["tools"] = tools
        capturado["model"] = model
        capturado["system_prompt"] = system_prompt
        capturado["checkpointer"] = checkpointer
        return "agente-chatbot-fake"

    monkeypatch.setattr(chatbot_agent, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        chatbot_agent,
        "ChatOpenAI",
        lambda model: f"openai-model::{model}",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    resultado = chatbot_agent.criar_agente_chatbot()

    nomes = {_tool_name(tool_obj) for tool_obj in capturado["tools"]}

    assert resultado == "agente-chatbot-fake"
    assert capturado["model"] == "openai-model::gpt-4o-mini"
    assert capturado["system_prompt"] == chatbot_agent.carregar_system_prompt()
    assert capturado["checkpointer"] is chatbot_agent.CHECKPOINTER
    assert "buscar_historico_de_pagamentos_do_servidor" in nomes
    assert "consultar_contratos" in nomes


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


def test_chatbot_agent_backend_reaproveita_agente_e_thread_id() -> None:
    calls: list[tuple[dict[str, object], dict[str, object]]] = []

    class FakeAgent:
        def invoke(self, payload, config):
            calls.append((payload, config))
            return {"messages": ["resposta final"]}

    fake_agent = FakeAgent()

    backend = ChatbotAgentBackend(agent_factory=lambda: fake_agent)
    primeira = backend.answer("qual o salario de ronaldo", session_id="sessao-teste")
    segunda = backend.answer("ronaldo gaspar", session_id="sessao-teste")

    assert primeira.content == "resposta final"
    assert segunda.content == "resposta final"
    assert calls == [
        (
            {"messages": ["qual o salario de ronaldo"]},
            {"configurable": {"thread_id": "sessao-teste"}},
        ),
        (
            {"messages": ["ronaldo gaspar"]},
            {"configurable": {"thread_id": "sessao-teste"}},
        ),
    ]


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
