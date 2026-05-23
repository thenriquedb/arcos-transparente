from __future__ import annotations

from agents.tools.registry import get_all_tools


def _tool_name(tool_obj) -> str:
    return getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))


def test_get_all_tools_descobre_tools_de_servidores() -> None:
    tools = get_all_tools()
    tool_names = {_tool_name(tool_obj) for tool_obj in tools}

    assert "buscar_servidores_por_nome" in tool_names
    assert "buscar_servidores_por_secretaria" in tool_names


def test_get_all_tools_nao_duplica_tools_em_chamadas_repetidas() -> None:
    primeira_chamada = get_all_tools()
    segunda_chamada = get_all_tools()

    nomes_primeira = [_tool_name(tool_obj) for tool_obj in primeira_chamada]
    nomes_segunda = [_tool_name(tool_obj) for tool_obj in segunda_chamada]

    assert nomes_primeira == nomes_segunda
    assert len(nomes_primeira) == len(set(nomes_primeira))
