from __future__ import annotations

from agents.tools.registry import (
    get_all_tools,
    get_public_tool_catalog,
    get_public_tools,
)


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
        "consultar_diarias",
        "agregar_diarias",
        "consultar_passagens",
        "agregar_passagens",
        "consultar_patrimonios",
        "agregar_patrimonios",
        "consultar_quadro_pessoal",
        "agregar_quadro_pessoal",
        "consultar_eleitos",
        "consultar_frota",
        "consultar_transferencias_financeiras",
        "agregar_transferencias_financeiras",
        "buscar_historico_de_pagamentos_do_servidor",
        "consultar_conhecimento_municipal",
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
        "consultar_diarias",
        "agregar_diarias",
        "consultar_passagens",
        "agregar_passagens",
        "consultar_patrimonios",
        "agregar_patrimonios",
        "consultar_quadro_pessoal",
        "agregar_quadro_pessoal",
        "consultar_eleitos",
        "consultar_frota",
        "consultar_transferencias_financeiras",
        "agregar_transferencias_financeiras",
        "buscar_historico_de_pagamentos_do_servidor",
        "consultar_conhecimento_municipal",
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


def test_catalogo_publico_expoe_metadados_de_roteamento_para_todas_as_tools() -> None:
    catalog = get_public_tool_catalog()

    assert len(catalog) == 26
    for entry in catalog:
        assert entry.routing.summary
        assert len(entry.routing.examples) >= 2
        assert len(entry.routing.hints) >= 3


def test_descricoes_orientam_salario_de_cargo_eleito_para_folha() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    consultar_eleitos = tools["consultar_eleitos"].description
    consultar_servidores = tools["consultar_servidores"].description
    buscar_historico = tools["buscar_historico_de_pagamentos_do_servidor"].description

    assert "salario do" in consultar_eleitos
    assert "prefeito" in consultar_eleitos
    assert "buscar_historico_de_pagamentos_do_servidor" in consultar_eleitos
    assert "NAO use para responder salario individual" in consultar_servidores
    assert "use antes `consultar_eleitos`" in consultar_servidores
    assert "primeiro use `consultar_eleitos`" in buscar_historico


def test_descricao_de_conhecimento_municipal_exige_citacao_e_limites() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    descricao = tools["consultar_conhecimento_municipal"].description
    descricao_frota = tools["consultar_frota"].description

    assert "telefones úteis" in descricao
    assert "arquivo_fonte" in descricao
    assert "NAO use esta tool como fonte final para salarios" in descricao
    assert "NAO use para horarios de onibus" in descricao_frota


def test_descricao_de_contratos_orienta_confirmar_siglas_ambiguas() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    descricao = tools["consultar_contratos"].description

    assert "sigla curta ou termo ambiguo" in descricao
    assert "UPA" in descricao
    assert "primeiro confirme o significado" in descricao


def test_descricoes_de_contratos_e_licitacoes_orientam_encadeamento() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    descricao_contratos = tools["consultar_contratos"].description
    descricao_licitacoes = tools["consultar_licitacoes"].description

    assert "R$ 0,00" in descricao_contratos
    assert "consultar_licitacoes" in descricao_contratos
    assert "consultar_despesas" in descricao_contratos
    assert "resultado vazio" in descricao_contratos
    assert "resultado vazio" in descricao_licitacoes
    assert "consultar_contratos" in descricao_licitacoes
    assert "valor estimado R$ 0,00" in descricao_licitacoes
