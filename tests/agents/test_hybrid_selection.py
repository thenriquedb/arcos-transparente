from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from agents.chatbot.hybrid_selection import HybridToolSelector
from agents.tools.registry import get_public_tools


def _tool_names(tools) -> tuple[str, ...]:
    return tuple(getattr(tool_obj, "name", "") for tool_obj in tools)


@dataclass(frozen=True)
class _HistoryMessage:
    role: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)


def test_hybrid_selector_restringe_para_candidates_validas() -> None:
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "allow",
            "candidate_tool_names": ["consultar_contratos", "consultar_licitacoes"],
            "confidence": "high",
            "reason_code": "cross_domain",
        }
    )

    selection = selector.select(
        "Quais contratos e licitacoes do festival gastronomico?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.candidate_tool_names == (
        "consultar_contratos",
        "consultar_licitacoes",
    )


def test_hybrid_selector_faz_fallback_para_catalogo_publico_em_baixa_confianca() -> None:
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "allow",
            "candidate_tool_names": ["consultar_contratos"],
            "confidence": "low",
            "reason_code": "uncertain",
        }
    )

    selection = selector.select("Quais contratos da saude?", history=[])

    assert selection.action == "allow"
    assert selection.used_fallback is True
    assert _tool_names(selection.candidate_tools) == _tool_names(get_public_tools())
    assert selection.reason_code == "uncertain"


def test_hybrid_selector_faz_fallback_quando_recebe_tool_desconhecida() -> None:
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "allow",
            "candidate_tool_names": ["tool_inexistente"],
            "confidence": "high",
            "reason_code": "invalid_name",
        }
    )

    selection = selector.select("Pergunta valida", history=[])

    assert selection.action == "allow"
    assert selection.used_fallback is True
    assert _tool_names(selection.candidate_tools) == _tool_names(get_public_tools())


def test_hybrid_selector_retorna_clarificacao_estruturada() -> None:
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "clarify",
            "candidate_tool_names": [],
            "confidence": "medium",
            "user_message": "Voce quer contratos ou licitacoes?",
            "reason_code": "needs_domain_split",
        }
    )

    selection = selector.select("Quais informacoes voce tem?", history=[])

    assert selection.action == "clarify"
    assert selection.message == "Voce quer contratos ou licitacoes?"
    assert selection.candidate_tools == ()


def test_hybrid_selector_prioriza_contato_de_eleitos_sem_chamar_modelo() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver contato de eleitos")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Como posso entrar em contato com os vereadores?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_elected_contacts"
    assert selection.candidate_tool_names == (
        "consultar_eleitos",
        "consultar_conhecimento_municipal",
    )


def test_hybrid_selector_prioriza_historico_de_salario_individual() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver salario individual")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto Lincoln manuel correa recebe?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_salary_history_query"
    assert selection.candidate_tool_names == ("buscar_historico_de_pagamentos_do_servidor",)


def test_hybrid_selector_reaproveita_historico_em_confirmacao_de_contato_de_eleitos() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria usar o historico")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "sim",
        history=[
            _HistoryMessage(
                role="user",
                content="Como posso entrar em contato com os vereadores?",
            ),
            _HistoryMessage(
                role="assistant",
                content=(
                    "Se desejar, posso tentar trazer a lista com os contatos "
                    "especificos dos vereadores eleitos para o mandato 2025-2028. "
                    "Quer que eu faca isso?"
                ),
            ),
        ],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_elected_contacts"
    assert selection.candidate_tool_names == (
        "consultar_eleitos",
        "consultar_conhecimento_municipal",
    )


def test_hybrid_selector_prioriza_ranking_de_maiores_contratos() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver ranking de contratos")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Liste os 10 maiores contratos de 2025.",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_contract_value_ranking"
    assert selection.candidate_tool_names == ("consultar_contratos",)


@pytest.mark.parametrize(
    "pergunta",
    [
        "Qual fornecedor tem mais contratos ativos hoje?",
        "Qual secretaria tem mais contratos?",
        "Qual categoria tem mais contratos atualmente?",
    ],
)
def test_hybrid_selector_prioriza_ranking_de_contratos_por_dimensao(
    pergunta: str,
) -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver ranking agregado de contratos")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(pergunta, history=[])

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_contract_count_ranking"
    assert selection.candidate_tool_names == ("agregar_contratos",)


def test_hybrid_selector_prioriza_emendas_por_autor() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver emendas por autor")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "quantas emendas foram do autor Cleitinho?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_emenda_query"
    assert selection.candidate_tool_names == ("agregar_transferencias_financeiras",)


def test_hybrid_selector_prioriza_ranking_de_estoques_por_movimentacao() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver ranking de estoques")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Qual é o ranking dos materiais com maior movimentação?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_estoques_query"
    assert selection.candidate_tool_names == ("agregar_estoques",)


def test_hybrid_selector_prioriza_movimentacoes_de_estoque() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver movimentacoes de estoque")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Liste as movimentacoes de estoque do almoxarifado saude em 2025.",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_estoques_query"
    assert selection.candidate_tool_names == ("consultar_movimentacoes_de_estoque",)


def test_hybrid_selector_prioriza_agregacao_de_itens_mais_comuns_no_almoxarifado() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver agregacao de estoques")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quais itens são mais comuns no almoxarifado?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_estoques_query"
    assert selection.candidate_tool_names == ("agregar_estoques",)


def test_hybrid_selector_prioriza_agregacao_de_entradas_de_estoque() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver entradas de estoque")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quais materiais tiveram mais entradas em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_estoques_query"
    assert selection.candidate_tool_names == ("agregar_estoques",)


def test_hybrid_selector_prioriza_candidates_de_custo_de_evento() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver custo de evento")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Qual foi o valor gasto com o festival gastronomico de 2026?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_event_spend_query"
    assert selection.candidate_tool_names == (
        "consultar_licitacoes",
        "consultar_contratos",
        "consultar_despesas",
    )


def test_hybrid_selector_prioriza_candidates_de_objeto_contratual_nominal() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver objeto contratual nominal")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto foi gasto com o Natal Fest em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_event_spend_query"
    assert selection.candidate_tool_names == (
        "consultar_licitacoes",
        "consultar_contratos",
        "consultar_despesas",
    )


def test_hybrid_selector_prioriza_candidates_de_shows_e_eventos() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver shows e eventos")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto foi gasto com shows e eventos em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_event_spend_query"
    assert selection.candidate_tool_names == (
        "consultar_licitacoes",
        "consultar_contratos",
        "consultar_despesas",
    )


def test_hybrid_selector_roteia_eventos_isolados_para_fan_out() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver gasto com eventos")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto foi gasto com eventos em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_event_spend_query"
    assert selection.candidate_tool_names == (
        "consultar_licitacoes",
        "consultar_contratos",
        "consultar_despesas",
    )


def test_hybrid_selector_roteia_shows_isolados_para_fan_out() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver gasto com shows")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto foi gasto com shows em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_event_spend_query"
    assert selection.candidate_tool_names == (
        "consultar_licitacoes",
        "consultar_contratos",
        "consultar_despesas",
    )


def test_hybrid_selector_combina_diarias_e_passagens_para_viagens_genericas() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria combinar diarias e passagens")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto a prefeitura gastou com viagens em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_travel_spend_query"
    assert selection.candidate_tool_names == (
        "consultar_diarias",
        "consultar_passagens",
    )


def test_hybrid_selector_total_por_funcao_preserva_quatro_estagios() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria preservar os quatro estagios")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Qual o total gasto com saude em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_function_spend_breakdown"
    assert selection.candidate_tool_names == ("consultar_despesas_por_funcao",)


def test_hybrid_selector_prioriza_fontes_de_viagem_por_mes() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria resolver diarias e viagens")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto a prefeitura gasta por mes com diarias e viagens?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_travel_spend_query"
    assert selection.candidate_tool_names == (
        "agregar_diarias",
        "agregar_passagens",
    )


def test_hybrid_selector_prioriza_lista_detalhada_de_diarias_em_gasto_amplo() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto a prefeitura gastou com diarias em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_diarias",)


def test_hybrid_selector_prioriza_lista_detalhada_de_passagens_em_gasto_amplo() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quais foram os gastos com passagens em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_passagens",)


def test_hybrid_selector_prioriza_lista_detalhada_de_despesas_em_gasto_amplo() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto a prefeitura gastou na saude em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_despesas_por_funcao",)


def test_hybrid_selector_prioriza_despesas_por_funcao_em_qual_foi_o_gasto() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Qual foi o gasto com saude em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_despesas_por_funcao",)


def test_hybrid_selector_prioriza_despesas_por_funcao_em_gasto_por_urbanismo() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto foi gasto com urbanismo em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_despesas_por_funcao",)


def test_hybrid_selector_prioriza_despesas_por_funcao_em_investimento_por_alias() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quanto foi investido em obras e pavimentacao em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_despesas_por_funcao",)


def test_hybrid_selector_prioriza_lista_detalhada_de_despesas_por_funcao() -> None:
    def _runner_nao_deve_ser_chamado(*_args, **_kwargs):
        raise AssertionError("heuristica deveria priorizar consulta detalhada")

    selector = HybridToolSelector(runner=_runner_nao_deve_ser_chamado)

    selection = selector.select(
        "Quais foram os gastos no relatorio de despesas por funcao em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "heuristic_broad_spend_query"
    assert selection.candidate_tool_names == ("consultar_despesas_por_funcao",)


def test_hybrid_selector_respeita_pedido_expresso_de_total_em_gasto() -> None:
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "allow",
            "candidate_tool_names": ["agregar_diarias"],
            "confidence": "high",
            "reason_code": "explicit_total_request",
        }
    )

    selection = selector.select(
        "Qual foi o total gasto com diarias em 2025?",
        history=[],
    )

    assert selection.action == "allow"
    assert selection.used_fallback is False
    assert selection.reason_code == "explicit_total_request"
    assert selection.candidate_tool_names == ("agregar_diarias",)
