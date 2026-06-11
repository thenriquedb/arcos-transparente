from __future__ import annotations

import pytest

from agents.nlu import intents


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("quantas emendas foram do autor cleitinho?", "agregar_transferencias_financeiras"),
        ("liste as emendas parlamentares de 2025", "consultar_transferencias_financeiras"),
        ("qual o telefone da camara?", None),
    ],
)
def test_emenda_tool(pergunta: str, esperado: str | None) -> None:
    assert intents.emenda_tool(pergunta) == esperado


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("qual e o ranking dos materiais com maior movimentacao?", "agregar_estoques"),
        ("quais itens sao mais comuns no almoxarifado?", "agregar_estoques"),
        (
            "liste as movimentacoes de estoque do almoxarifado saude em 2025",
            "consultar_movimentacoes_de_estoque",
        ),
        ("qual o saldo de material papel a4?", "consultar_estoques"),
        ("qual o salario do prefeito?", None),
    ],
)
def test_estoque_tool(pergunta: str, esperado: str | None) -> None:
    assert intents.estoque_tool(pergunta) == esperado


def test_contract_rankings_sao_distintos() -> None:
    assert intents.contract_value_ranking_query("liste os 10 maiores contratos de 2025") is True
    assert intents.contract_count_ranking_query("liste os 10 maiores contratos de 2025") is False

    assert intents.contract_count_ranking_query("qual fornecedor tem mais contratos ativos hoje?") is True
    assert intents.contract_value_ranking_query("qual fornecedor tem mais contratos ativos hoje?") is False


def test_function_spend_broad_total_preserva_quatro_estagios() -> None:
    assert intents.is_function_spend_broad_total("qual o total gasto com saude em 2025?") is True
    # Pedido com agrupamento explícito é um agregado legítimo, não o total amplo.
    assert intents.is_function_spend_broad_total("quanto foi gasto com saude por unidade gestora em 2025?") is False


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("quanto a prefeitura gastou com diarias em 2025?", ["consultar_diarias"]),
        ("quais foram os gastos com passagens em 2025?", ["consultar_passagens"]),
        ("quanto a prefeitura gastou na saude em 2025?", ["consultar_despesas_por_funcao"]),
        ("qual a capital da franca?", None),
    ],
)
def test_direct_spend_domain_tools(pergunta: str, esperado: list[str] | None) -> None:
    assert intents.direct_spend_domain_tools(pergunta) == esperado
