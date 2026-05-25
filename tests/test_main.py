from __future__ import annotations

import main


def _tool_name(tool_obj) -> str:
    return getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))


def test_criar_agente_sem_pergunta_usa_so_tools_publicas(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    def fake_create_agent(*, tools, model, system_prompt):
        capturado["tools"] = tools
        capturado["model"] = model
        capturado["system_prompt"] = system_prompt
        return "agente-fake"

    monkeypatch.setattr(main, "create_agent", fake_create_agent)

    resultado = main.criar_agente()

    nomes = {_tool_name(tool_obj) for tool_obj in capturado["tools"]}

    assert resultado == "agente-fake"
    assert capturado["model"] == "gpt-4o-mini"
    assert "use as tools disponíveis antes de responder" in capturado["system_prompt"]
    assert "consultar_servidores" in capturado["system_prompt"]
    assert nomes == {
        "consultar_servidores",
        "agregar_servidores",
        "buscar_historico_de_pagamentos_do_servidor",
    }


def test_criar_agente_com_pergunta_de_top_salarios_restringe_toolset(
    monkeypatch,
) -> None:
    capturado: dict[str, object] = {}

    def fake_create_agent(*, tools, model, system_prompt):
        capturado["tools"] = tools
        capturado["model"] = model
        capturado["system_prompt"] = system_prompt
        return "agente-fake"

    monkeypatch.setattr(main, "create_agent", fake_create_agent)

    resultado = main.criar_agente("Quais os 10 maiores salários da prefeitura?")

    nomes = [_tool_name(tool_obj) for tool_obj in capturado["tools"]]

    assert resultado == "agente-fake"
    assert nomes == ["consultar_servidores"]
