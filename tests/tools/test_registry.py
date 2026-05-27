from __future__ import annotations

from agents.tools.registry import get_all_tools, get_public_tools


def _tool_name(tool_obj) -> str:
    return getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))


def test_get_public_tools_reduz_superficie_para_capabilidades_publicas() -> None:
    public_tool_names = {_tool_name(tool_obj) for tool_obj in get_public_tools()}

    assert public_tool_names == {
        "consultar_servidores",
        "agregar_servidores",
        "consultar_contratos",
        "agregar_contratos",
        "consultar_licitacoes",
        "agregar_licitacoes",
        "consultar_receitas",
        "agregar_receitas",
        "consultar_planejamento",
        "agregar_planejamento",
        "consultar_despesas",
        "agregar_despesas",
        "consultar_patrimonios",
        "agregar_patrimonios",
        "consultar_quadro_pessoal",
        "agregar_quadro_pessoal",
        "consultar_eleitos",
        "buscar_historico_de_pagamentos_do_servidor",
    }


def test_get_all_tools_converge_para_mesma_superficie_publica() -> None:
    tool_names = {_tool_name(tool_obj) for tool_obj in get_all_tools()}

    assert tool_names == {
        "consultar_servidores",
        "agregar_servidores",
        "consultar_contratos",
        "agregar_contratos",
        "consultar_licitacoes",
        "agregar_licitacoes",
        "consultar_receitas",
        "agregar_receitas",
        "consultar_planejamento",
        "agregar_planejamento",
        "consultar_despesas",
        "agregar_despesas",
        "consultar_patrimonios",
        "agregar_patrimonios",
        "consultar_quadro_pessoal",
        "agregar_quadro_pessoal",
        "consultar_eleitos",
        "buscar_historico_de_pagamentos_do_servidor",
    }


def test_get_all_tools_nao_expoe_nomes_antigos_de_servidores() -> None:
    tool_names = {_tool_name(tool_obj) for tool_obj in get_all_tools()}

    assert "buscar_servidores_por_nome" not in tool_names
    assert "buscar_servidores_por_secretaria" not in tool_names
    assert "listar_servidores_da_secretaria" not in tool_names
    assert "contar_servidores_por_secretaria" not in tool_names
    assert "buscar_servidores_por_cargo" not in tool_names
    assert "listar_maiores_salarios" not in tool_names
    assert "buscar_servidores_por_mes_de_referencia_no_periodo" not in tool_names
    assert "listar_secretarias_por_quantidade_de_servidores" not in tool_names
    assert "buscar_secretaria_com_mais_servidores" not in tool_names


def test_get_all_tools_nao_duplica_tools_em_chamadas_repetidas() -> None:
    primeira_chamada = get_all_tools()
    segunda_chamada = get_all_tools()

    nomes_primeira = [_tool_name(tool_obj) for tool_obj in primeira_chamada]
    nomes_segunda = [_tool_name(tool_obj) for tool_obj in segunda_chamada]

    assert nomes_primeira == nomes_segunda
    assert len(nomes_primeira) == len(set(nomes_primeira))
