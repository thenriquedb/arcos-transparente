from __future__ import annotations

from dataclasses import dataclass, field

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


def test_hybrid_selector_faz_fallback_para_catalogo_publico_em_baixa_confianca() -> (
    None
):
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

    selection = selector.select("Quais gastos do evento?", history=[])

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


def test_hybrid_selector_reaproveita_historico_em_confirmacao_de_contato_de_eleitos() -> (
    None
):
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
