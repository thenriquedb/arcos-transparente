from __future__ import annotations

import main


def _tool_name(tool_obj) -> str:
    return getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))


def test_criar_agente_passa_tools_registradas_para_o_langchain(monkeypatch) -> None:
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
    assert "rankings de salários" in capturado["system_prompt"]
    assert "buscar_servidores_por_nome" in nomes
    assert "buscar_servidores_por_secretaria" in nomes
    assert "listar_maiores_salarios" in nomes
