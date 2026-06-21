"""Selecao hibrida de tools para o chatbot cidadao."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from agents.chatbot.agent import criar_modelo_llm
from agents.chatbot.observability import (
    NoOpObservabilityProvider,
    ObservabilityProvider,
    build_event_payload,
)
from agents.nlu import intents
from agents.nlu.constants import (
    DIARIAS_DOMAIN_KEYWORDS,
    PASSAGENS_DOMAIN_KEYWORDS,
)
from agents.nlu.conversation import (
    looks_like_confirmation_text,
    normalize_conversation_terms,
    normalize_conversation_text,
)
from agents.nlu.detectors import strip_despesas_por_funcao_domain_keywords
from agents.nlu.reading import read_query
from agents.tools.names import ToolName
from agents.tools.registry import (
    PublicToolCatalogEntry,
    get_public_tool_catalog,
    get_public_tools,
    get_public_tools_by_name,
)


SelectorAction = Literal["allow", "clarify", "block"]
SelectorConfidence = Literal["high", "medium", "low"]

_MAX_SELECTOR_CANDIDATES = 4
_CONTEXT_WINDOW = 6
_CONTACT_QUERY_TERMS = (
    "contato",
    "contatos",
    "email",
    "e-mail",
    "telefone",
    "telefones",
    "whatsapp",
    "homepage",
    "site",
)
_ELECTED_QUERY_TERMS = (
    "vereador",
    "vereadores",
    "vereadora",
    "vereadoras",
    "prefeito",
    "prefeita",
    "vice-prefeito",
    "vice prefeito",
    "viceprefeito",
    "eleito",
    "eleitos",
)
_EVENT_SPEND_SIGNAL_TERMS = (
    "gasto",
    "gastos",
    "gastou",
    "gasta",
    "gastam",
    "custo",
    "custou",
    "investido",
    "investida",
    "investimento",
    "investimentos",
    "valor gasto",
)
_SPEND_AGGREGATION_TERMS = (
    "total",
    "somatorio",
    "soma",
    "ranking",
    "rankings",
    "principal",
    "principais",
    "comparacao",
    "comparacoes",
    "comparativo",
    "comparativos",
    "media",
    "medias",
    "top ",
    "maior",
    "maiores",
    "menor",
    "menores",
    "quantas",
    "quantos",
)
_GENERIC_TRAVEL_TERMS = (
    "viagem",
    "viagens",
)
_SPEND_GROUPING_TERMS = (
    "por beneficiario",
    "por origem",
    "por unidade",
    "por unidade gestora",
    "por categoria",
    "por credor",
    "por mes",
    "por area",
    "por funcao",
    "por tipo",
)
_SERVIDOR_LOOKUP_TERMS = (
    "servidor",
    "servidora",
    "funcionario",
    "funcionaria",
)
_SERVIDOR_CAMARA_TERMS = (
    "camara",
    "legislativo",
)
_SERVIDOR_PREFEITURA_TERMS = ("prefeitura",)
_SERVIDOR_AGGREGATE_SIGNALS = (
    "quantos",
    "quantas",
    "total",
    "soma",
    "ranking",
    "contagem",
    "por cargo",
    "por lotacao",
    "por secretaria",
    "massa salarial",
)
_FROTA_DOMAIN_TERMS = (
    "frota",
    "veiculo",
    "veiculos",
    "placa",
    "placas",
    "onibus",
    "ambulancia",
    "van",
    "retroescavadeira",
    "caminhao",
)
_FROTA_VEHICLE_RANKING_CUES = (
    "quais veiculos",
    "veiculos que mais",
    "veiculos mais",
    "placas que mais",
    "placas com mais",
    "tipo de veiculo",
    "tipos de veiculo",
)
_FROTA_EXPENSE_QUERY_CUES = (
    "gastos dos veiculos",
    "gastos dos veiculos da prefeitura",
    "gastos com a frota",
    "gastos da frota",
    "despesas dos veiculos",
    "despesas dos veiculos da prefeitura",
    "despesas da frota",
    "despesas com a frota",
    "manutencao da frota",
    "combustivel da frota",
    "tipos de gasto",
    "tipos de despesa",
    "principais gastos",
    "principais despesas",
)


class HistoryMessage(Protocol):
    role: str
    content: str
    metadata: Mapping[str, Any]


class HybridSelectorDecisionPayload(BaseModel):
    """Payload estruturado esperado do seletor model-based."""

    action: SelectorAction
    candidate_tool_names: list[str] = Field(default_factory=list)
    confidence: SelectorConfidence = "low"
    user_message: str | None = None
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class HybridToolSelection:
    """Resultado consolidado usado pelo runtime antes de criar o agente."""

    action: SelectorAction
    candidate_tools: tuple[object, ...]
    candidate_tool_names: tuple[str, ...]
    confidence: SelectorConfidence
    message: str | None = None
    reason_code: str | None = None
    used_fallback: bool = False


class HybridToolSelector:
    """Seleciona tools publicas candidatas com fallback seguro."""

    def __init__(
        self,
        *,
        runner: Callable[
            [str, Sequence[HistoryMessage], Sequence[PublicToolCatalogEntry]],
            Any,
        ]
        | None = None,
        catalog_factory: Callable[[], list[PublicToolCatalogEntry]] = (get_public_tool_catalog),
        observability_provider: ObservabilityProvider | None = None,
    ) -> None:
        self._runner = runner or _run_model_selector
        self._catalog_factory = catalog_factory
        self._observability_provider = observability_provider or NoOpObservabilityProvider()

    def set_observability_provider(
        self,
        provider: ObservabilityProvider,
    ) -> None:
        self._observability_provider = provider

    def select(
        self,
        question: str,
        *,
        history: Sequence[HistoryMessage],
        request_id: str | None = None,
        session_id: str | None = None,
    ) -> HybridToolSelection:
        catalog = tuple(self._catalog_factory())
        if not catalog:
            selection = _fallback_selection(reason_code="empty_catalog")
            self._emit_selection_observation(
                question,
                history=history,
                selection=selection,
                request_id=request_id,
                session_id=session_id,
            )
            return selection

        heuristic_selection = _select_with_heuristics(question, history=history)
        if heuristic_selection is not None:
            self._emit_selection_observation(
                question,
                history=history,
                selection=heuristic_selection,
                request_id=request_id,
                session_id=session_id,
            )
            return heuristic_selection

        all_public_tools = tuple(entry.tool for entry in catalog)
        all_tool_names = tuple(entry.name for entry in catalog)
        try:
            raw_decision = self._runner(question, history, catalog)
        except Exception:
            selection = _fallback_selection(
                tools=all_public_tools,
                tool_names=all_tool_names,
                reason_code="selector_error",
            )
            self._emit_selection_observation(
                question,
                history=history,
                selection=selection,
                request_id=request_id,
                session_id=session_id,
            )
            return selection

        decision = _coerce_selector_payload(raw_decision)
        if decision is None:
            selection = _fallback_selection(
                tools=all_public_tools,
                tool_names=all_tool_names,
                reason_code="invalid_selector_output",
            )
            self._emit_selection_observation(
                question,
                history=history,
                selection=selection,
                request_id=request_id,
                session_id=session_id,
            )
            return selection

        if decision.action == "allow":
            selection = _resolve_allow_selection(
                decision,
                fallback_tools=all_public_tools,
                fallback_tool_names=all_tool_names,
            )
            self._emit_selection_observation(
                question,
                history=history,
                selection=selection,
                request_id=request_id,
                session_id=session_id,
            )
            return selection

        if not decision.user_message:
            selection = _fallback_selection(
                tools=all_public_tools,
                tool_names=all_tool_names,
                reason_code="missing_selector_message",
            )
            self._emit_selection_observation(
                question,
                history=history,
                selection=selection,
                request_id=request_id,
                session_id=session_id,
            )
            return selection

        selection = HybridToolSelection(
            action=decision.action,
            candidate_tools=(),
            candidate_tool_names=(),
            confidence=decision.confidence,
            message=decision.user_message,
            reason_code=decision.reason_code,
        )
        self._emit_selection_observation(
            question,
            history=history,
            selection=selection,
            request_id=request_id,
            session_id=session_id,
        )
        return selection

    def _emit_selection_observation(
        self,
        question: str,
        *,
        history: Sequence[HistoryMessage],
        selection: HybridToolSelection,
        request_id: str | None,
        session_id: str | None,
    ) -> None:
        self._observability_provider.emit_event(
            "chatbot.selection",
            inputs=build_event_payload(
                {
                    "request_id": request_id,
                    "session_id": session_id,
                    "question": question,
                    "history_size": len(history),
                }
            ),
            outputs=build_event_payload(
                {
                    "selection_action": selection.action,
                    "selection_confidence": selection.confidence,
                    "selection_reason_code": selection.reason_code,
                    "selection_fallback": selection.used_fallback,
                    "selected_tool_names": list(selection.candidate_tool_names),
                    "candidate_tool_names": list(selection.candidate_tool_names),
                    "status": selection.action,
                }
            ),
            tags=("chatbot", "selection"),
        )


def _resolve_allow_selection(
    decision: HybridSelectorDecisionPayload,
    *,
    fallback_tools: Sequence[object],
    fallback_tool_names: Sequence[str],
) -> HybridToolSelection:
    if decision.confidence == "low":
        return _fallback_selection(
            tools=fallback_tools,
            tool_names=fallback_tool_names,
            reason_code=decision.reason_code or "low_confidence",
        )

    candidate_names = _normalize_candidate_names(decision.candidate_tool_names)
    if not candidate_names:
        return _fallback_selection(
            tools=fallback_tools,
            tool_names=fallback_tool_names,
            reason_code=decision.reason_code or "empty_candidate_set",
        )

    candidate_tools = tuple(get_public_tools_by_name(candidate_names))
    if len(candidate_tools) != len(candidate_names):
        return _fallback_selection(
            tools=fallback_tools,
            tool_names=fallback_tool_names,
            reason_code=decision.reason_code or "unknown_candidate_tools",
        )

    return HybridToolSelection(
        action="allow",
        candidate_tools=candidate_tools,
        candidate_tool_names=tuple(candidate_names),
        confidence=decision.confidence,
        reason_code=decision.reason_code,
    )


def _fallback_selection(
    *,
    tools: Sequence[object] | None = None,
    tool_names: Sequence[str] | None = None,
    reason_code: str,
) -> HybridToolSelection:
    fallback_tools = tuple(tools or get_public_tools())
    fallback_tool_names = tuple(tool_names or [getattr(tool_obj, "name", "") for tool_obj in fallback_tools])
    return HybridToolSelection(
        action="allow",
        candidate_tools=fallback_tools,
        candidate_tool_names=fallback_tool_names,
        confidence="low",
        reason_code=reason_code,
        used_fallback=True,
    )


def _build_named_candidate_selection(
    candidate_tool_names: Sequence[str],
    *,
    reason_code: str,
    confidence: SelectorConfidence = "high",
) -> HybridToolSelection | None:
    candidate_names = _normalize_candidate_names(candidate_tool_names)
    candidate_tools = tuple(get_public_tools_by_name(candidate_names))
    if len(candidate_tools) != len(candidate_names):
        return None

    return HybridToolSelection(
        action="allow",
        candidate_tools=candidate_tools,
        candidate_tool_names=tuple(candidate_names),
        confidence=confidence,
        reason_code=reason_code,
    )


def _select_with_heuristics(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> HybridToolSelection | None:
    if not _is_elected_contact_query(question, history=history):
        salary_history_selection = _select_salary_history_with_router(question)
        if salary_history_selection is not None:
            return salary_history_selection
        planning_spend_selection = _select_planning_spend_query(question)
        if planning_spend_selection is not None:
            return planning_spend_selection
        travel_spend_selection = _select_travel_spend_query(question)
        if travel_spend_selection is not None:
            return travel_spend_selection
        spend_selection = _select_broad_spend_query(question)
        if spend_selection is not None:
            return spend_selection
        function_spend_selection = _select_function_spend_breakdown_query(question)
        if function_spend_selection is not None:
            return function_spend_selection
        emenda_selection = _select_emenda_query_with_router(question)
        if emenda_selection is not None:
            return emenda_selection
        contract_count_ranking_selection = _select_contract_count_ranking_with_router(question)
        if contract_count_ranking_selection is not None:
            return contract_count_ranking_selection
        contract_ranking_selection = _select_contract_value_ranking_with_router(question)
        if contract_ranking_selection is not None:
            return contract_ranking_selection
        estoques_selection = _select_estoques_query_with_router(question)
        if estoques_selection is not None:
            return estoques_selection
        frota_spend_selection = _select_frota_spend_query(question)
        if frota_spend_selection is not None:
            return frota_spend_selection
        servidor_cross_search_selection = _select_servidor_cross_search(question)
        if servidor_cross_search_selection is not None:
            return servidor_cross_search_selection
        return None

    return _build_named_candidate_selection(
        [
            ToolName.CONSULTAR_ELEITOS,
            ToolName.CONSULTAR_CONHECIMENTO_MUNICIPAL,
        ],
        reason_code="heuristic_elected_contacts",
    )


def _resolve_servidor_entity_context(normalized_text: str) -> str | None:
    """Detecta contexto de entidade numa query de servidor.

    Retorna ``'camara'``, ``'prefeitura'`` ou ``None`` (ambíguo).
    Usado por todas as heurísticas de servidor para decidir se aplica
    cross-search (ambas as bases) ou roteamento direto para uma entidade.
    """
    if _has_any_term(normalized_text, _SERVIDOR_CAMARA_TERMS):
        return "camara"
    if _has_any_term(normalized_text, _SERVIDOR_PREFEITURA_TERMS):
        return "prefeitura"
    return None


def _select_salary_history_with_router(
    question: str,
) -> HybridToolSelection | None:
    if read_query(question).nome_historico is None:
        return None
    normalized = normalize_conversation_text(question)
    entity = _resolve_servidor_entity_context(normalized)
    if entity == "camara":
        return _build_named_candidate_selection(
            [ToolName.CONSULTAR_SERVIDORES_CAMARA],
            reason_code="heuristic_salary_history_query",
        )
    if entity == "prefeitura":
        return _build_named_candidate_selection(
            [ToolName.BUSCAR_HISTORICO_DE_PAGAMENTOS_DO_SERVIDOR],
            reason_code="heuristic_salary_history_query",
        )
    return _build_named_candidate_selection(
        [ToolName.BUSCAR_HISTORICO_DE_PAGAMENTOS_DO_SERVIDOR, ToolName.CONSULTAR_SERVIDORES_CAMARA],
        reason_code="heuristic_salary_history_cross_search",
    )


def _select_planning_spend_query(
    question: str,
) -> HybridToolSelection | None:
    reading = read_query(question)
    if not reading.normalized_text:
        return None
    has_planning_specific_filter = any(
        (
            reading.planejamento_programa,
            reading.planejamento_acao,
            reading.planejamento_fonte_recurso,
        )
    )
    if not has_planning_specific_filter:
        return None
    if not any(signal in reading.normalized_text for signal in _EVENT_SPEND_SIGNAL_TERMS):
        return None

    aggregate_first = _looks_like_total_spend_question(reading.normalized_text)
    candidate_tool_names = (
        [
            ToolName.AGREGAR_PLANEJAMENTO,
            ToolName.CONSULTAR_PLANEJAMENTO,
        ]
        if aggregate_first
        else [
            ToolName.CONSULTAR_PLANEJAMENTO,
            ToolName.AGREGAR_PLANEJAMENTO,
        ]
    )
    return _build_named_candidate_selection(
        candidate_tool_names,
        reason_code="heuristic_planning_program_spend_query",
    )


def _select_event_spend_query(
    question: str,
) -> HybridToolSelection | None:
    reading = read_query(question)
    if not reading.normalized_text:
        return None
    if not any(signal in reading.normalized_text for signal in _EVENT_SPEND_SIGNAL_TERMS):
        return None
    if reading.licitacoes_objeto is None:
        return None

    return _build_named_candidate_selection(
        [
            ToolName.CONSULTAR_LICITACOES,
            ToolName.CONSULTAR_CONTRATOS,
            ToolName.CONSULTAR_DESPESAS,
        ],
        reason_code="heuristic_event_spend_query",
    )


def _select_travel_spend_query(
    question: str,
) -> HybridToolSelection | None:
    normalized_question = normalize_conversation_text(question)
    if not normalized_question:
        return None
    if not any(signal in normalized_question for signal in _EVENT_SPEND_SIGNAL_TERMS):
        return None

    has_diarias = _has_any_term(normalized_question, DIARIAS_DOMAIN_KEYWORDS)
    has_passagens = _has_any_term(normalized_question, PASSAGENS_DOMAIN_KEYWORDS)
    has_generic_travel = _has_any_term(normalized_question, _GENERIC_TRAVEL_TERMS)
    # "Viagem/viagens" genérico cobre diárias + passagens (o custo de viagem do
    # cidadão inclui ambos), além do caso em que os dois domínios são citados.
    if not (has_diarias and has_passagens) and not has_generic_travel:
        return None

    candidate_tool_names = (
        [ToolName.AGREGAR_DIARIAS, ToolName.AGREGAR_PASSAGENS]
        if _is_explicit_aggregate_spend_request(normalized_question)
        else [ToolName.CONSULTAR_DIARIAS, ToolName.CONSULTAR_PASSAGENS]
    )
    return _build_named_candidate_selection(
        candidate_tool_names,
        reason_code="heuristic_travel_spend_query",
    )


def _select_broad_spend_query(
    question: str,
) -> HybridToolSelection | None:
    event_spend_selection = _select_event_spend_query(question)
    if event_spend_selection is not None:
        return event_spend_selection

    normalized_question = normalize_conversation_text(question)
    if not normalized_question:
        return None
    if not any(signal in normalized_question for signal in _EVENT_SPEND_SIGNAL_TERMS):
        return None
    if _is_explicit_aggregate_spend_request(normalized_question):
        return None

    direct_domain_candidate_names = intents.direct_spend_domain_tools(normalized_question)
    if direct_domain_candidate_names is None:
        return None

    return _build_named_candidate_selection(
        direct_domain_candidate_names,
        reason_code="heuristic_broad_spend_query",
    )


def _select_function_spend_breakdown_query(
    question: str,
) -> HybridToolSelection | None:
    """Mantém a regra dos quatro estágios para gasto amplo por função de governo.

    Um "total gasto com [função]" não deve colapsar em um único `valor_pago`
    agregado: roteia para `consultar_despesas_por_funcao`, que expõe
    `valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado` e `valor_pago`.
    """

    if not intents.is_function_spend_broad_total(normalize_conversation_text(question)):
        return None

    return _build_named_candidate_selection(
        [ToolName.CONSULTAR_DESPESAS_POR_FUNCAO],
        reason_code="heuristic_function_spend_breakdown",
    )


def _is_explicit_aggregate_spend_request(normalized_question: str) -> bool:
    aggregate_text = strip_despesas_por_funcao_domain_keywords(normalized_question)
    if any(term in aggregate_text for term in _SPEND_GROUPING_TERMS):
        return True
    return any(term in aggregate_text for term in _SPEND_AGGREGATION_TERMS)


def _looks_like_total_spend_question(normalized_question: str) -> bool:
    if _is_explicit_aggregate_spend_request(normalized_question):
        return True
    return any(
        cue in normalized_question
        for cue in (
            "qual foi o gasto",
            "qual o gasto",
            "qual foi o valor gasto",
            "quanto foi gasto",
            "quanto a prefeitura gastou",
            "quanto gastou",
            "quanto custou",
            "valor gasto",
        )
    )


def _select_emenda_query_with_router(
    question: str,
) -> HybridToolSelection | None:
    tool_name = intents.emenda_tool(normalize_conversation_text(question))
    if tool_name is None:
        return None
    return _build_named_candidate_selection(
        [tool_name],
        reason_code="heuristic_emenda_query",
    )


def _select_contract_value_ranking_with_router(
    question: str,
) -> HybridToolSelection | None:
    if not intents.contract_value_ranking_query(normalize_conversation_text(question)):
        return None
    return _build_named_candidate_selection(
        [ToolName.CONSULTAR_CONTRATOS],
        reason_code="heuristic_contract_value_ranking",
    )


def _select_contract_count_ranking_with_router(
    question: str,
) -> HybridToolSelection | None:
    if not intents.contract_count_ranking_query(normalize_conversation_text(question)):
        return None
    return _build_named_candidate_selection(
        [ToolName.AGREGAR_CONTRATOS],
        reason_code="heuristic_contract_count_ranking",
    )


def _select_estoques_query_with_router(
    question: str,
) -> HybridToolSelection | None:
    tool_name = intents.estoque_tool(normalize_conversation_text(question))
    if tool_name is None:
        return None
    return _build_named_candidate_selection(
        [tool_name],
        reason_code="heuristic_estoques_query",
    )


def _select_frota_spend_query(
    question: str,
) -> HybridToolSelection | None:
    normalized_question = normalize_conversation_text(question)
    if not normalized_question:
        return None
    if not _has_any_term(normalized_question, _FROTA_DOMAIN_TERMS):
        return None
    if not any(signal in normalized_question for signal in _EVENT_SPEND_SIGNAL_TERMS):
        return None
    if any(cue in normalized_question for cue in _FROTA_VEHICLE_RANKING_CUES):
        return _build_named_candidate_selection(
            [ToolName.AGREGAR_FROTA],
            reason_code="heuristic_frota_vehicle_spend_ranking",
        )
    if any(cue in normalized_question for cue in _FROTA_EXPENSE_QUERY_CUES):
        tool_name = (
            ToolName.AGREGAR_DESPESAS_FROTA
            if _is_explicit_aggregate_spend_request(normalized_question)
            else ToolName.CONSULTAR_DESPESAS_FROTA
        )
        return _build_named_candidate_selection(
            [tool_name],
            reason_code="heuristic_frota_spend_query",
        )
    return None


def _select_servidor_cross_search(
    question: str,
) -> HybridToolSelection | None:
    """Garante candidatos duplos ao buscar servidor por nome sem contexto de entidade.

    Quando a pergunta menciona um termo de domínio de servidor (servidor, funcionário…)
    mas NÃO especifica câmara ou prefeitura via ``_resolve_servidor_entity_context``,
    e NÃO é uma agregação, expõe ambas as tools de lookup para o agente consultar
    as duas bases.
    """
    normalized = normalize_conversation_text(question)
    if not _has_any_term(normalized, _SERVIDOR_LOOKUP_TERMS):
        return None
    if _has_any_term(normalized, _SERVIDOR_AGGREGATE_SIGNALS):
        return None
    if _resolve_servidor_entity_context(normalized) is not None:
        return None
    return _build_named_candidate_selection(
        [ToolName.CONSULTAR_SERVIDORES, ToolName.CONSULTAR_SERVIDORES_CAMARA],
        reason_code="heuristic_servidor_cross_search",
    )


def _normalize_candidate_names(candidate_tool_names: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for tool_name in candidate_tool_names:
        cleaned = str(tool_name).strip()
        if not cleaned or cleaned in normalized:
            continue
        normalized.append(cleaned)
        if len(normalized) >= _MAX_SELECTOR_CANDIDATES:
            break
    return normalized


def _coerce_selector_payload(raw_decision: Any) -> HybridSelectorDecisionPayload | None:
    if isinstance(raw_decision, HybridSelectorDecisionPayload):
        return raw_decision

    if isinstance(raw_decision, BaseModel):
        try:
            return HybridSelectorDecisionPayload.model_validate(raw_decision.model_dump())
        except ValidationError:
            return None

    if isinstance(raw_decision, Mapping):
        try:
            return HybridSelectorDecisionPayload.model_validate(dict(raw_decision))
        except ValidationError:
            return None

    if isinstance(raw_decision, str):
        try:
            parsed = json.loads(raw_decision)
        except json.JSONDecodeError:
            return None
        return _coerce_selector_payload(parsed)

    return None


def _is_elected_contact_query(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> bool:
    normalized_question = normalize_conversation_terms(question)
    if not normalized_question:
        return False

    has_contact_in_question = _has_any_term(
        normalized_question,
        _CONTACT_QUERY_TERMS,
    )
    has_elected_in_question = _has_any_term(
        normalized_question,
        _ELECTED_QUERY_TERMS,
    )
    if has_contact_in_question and has_elected_in_question:
        return True

    history_text = " ".join(
        normalize_conversation_terms(message.content)
        for message in history[-_CONTEXT_WINDOW:]
        if str(message.content).strip()
    ).strip()
    if not history_text:
        return False

    if looks_like_confirmation_text(normalize_conversation_terms(question)):
        return _has_any_term(history_text, _CONTACT_QUERY_TERMS) and _has_any_term(
            history_text,
            _ELECTED_QUERY_TERMS,
        )

    if has_contact_in_question and _has_any_term(history_text, _ELECTED_QUERY_TERMS):
        return True

    if has_elected_in_question and _has_any_term(history_text, _CONTACT_QUERY_TERMS):
        return True

    return False


def _has_any_term(text: str, terms: Sequence[str]) -> bool:
    return any(term in text for term in terms)


def _run_model_selector(
    question: str,
    history: Sequence[HistoryMessage],
    catalog: Sequence[PublicToolCatalogEntry],
) -> Any:
    model = criar_modelo_llm()
    prompt = _build_selector_prompt(question, history=history, catalog=catalog)
    response = model.invoke(prompt)
    return _extract_model_text(response)


def _build_selector_prompt(
    question: str,
    *,
    history: Sequence[HistoryMessage],
    catalog: Sequence[PublicToolCatalogEntry],
) -> str:
    history_payload = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in history[-_CONTEXT_WINDOW:]
    ]
    catalog_payload = [
        {
            "name": entry.name,
            "summary": entry.routing.summary,
            "examples": list(entry.routing.examples),
            "hints": list(entry.routing.hints),
            "tags": list(entry.tags),
            "exclusions": list(entry.routing.exclusions),
        }
        for entry in catalog
    ]
    schema = HybridSelectorDecisionPayload.model_json_schema()
    return (
        "Você é um seletor de tools do chatbot cidadão de transparência pública.\n"
        "Escolha apenas as tools públicas mais plausíveis para responder a pergunta "
        "permitida do usuário.\n"
        "Regras:\n"
        "- Retorne SOMENTE JSON válido aderente ao schema fornecido.\n"
        "- Use action='allow' quando conseguir sugerir uma lista pequena e útil de "
        "tools candidatas.\n"
        "- Use action='clarify' quando a pergunta ainda precisar de uma pergunta "
        "objetiva antes da execução.\n"
        "- Use action='block' apenas se a pergunta permitida ainda exigir uma recusa "
        "curta por impossibilidade operacional.\n"
        "- Para action='allow', prefira de 1 a 4 tools.\n"
        "- Para perguntas multi-domínio, você pode escolher mais de uma tool.\n"
        "- Use confidence='low' se estiver em dúvida entre muitas families de tools.\n"
        "- Quando a pergunta atual for um refinamento curto do histórico "
        "(por exemplo por autor, função, ano ou ranking), preserve o domínio já "
        "estabelecido na conversa em vez de tratar a pergunta como um tema novo.\n\n"
        f"Schema JSON:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"Histórico recente:\n{json.dumps(history_payload, ensure_ascii=False)}\n\n"
        f"Pergunta atual:\n{json.dumps(question, ensure_ascii=False)}\n\n"
        f"Catálogo público:\n{json.dumps(catalog_payload, ensure_ascii=False)}\n"
    )


def _extract_model_text(response: Any) -> str:
    if isinstance(response, str):
        return response

    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, Mapping):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)
