"""Selecao hibrida de tools para o chatbot cidadao."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import re
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from agents.chatbot.agent import criar_modelo_llm
from agents.chatbot.observability import (
    NoOpObservabilityProvider,
    ObservabilityProvider,
    build_event_payload,
)
from agents.routing.compatibility import route_public_compatibility_query
from agents.routing.conversation import (
    looks_like_confirmation_text,
    normalize_conversation_terms,
    normalize_conversation_text,
)
from agents.routing.constants import (
    DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS,
    DESPESAS_DOMAIN_KEYWORDS,
    DIARIAS_DOMAIN_KEYWORDS,
    PASSAGENS_DOMAIN_KEYWORDS,
)
from agents.routing.extractors import _extract_licitacoes_objeto
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
    "custo",
    "custou",
    "valor gasto",
)
_SPEND_AGGREGATION_TERMS = (
    "total",
    "somatorio",
    "soma",
    "ranking",
    "rankings",
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
        catalog_factory: Callable[[], list[PublicToolCatalogEntry]] = (
            get_public_tool_catalog
        ),
        observability_provider: ObservabilityProvider | None = None,
    ) -> None:
        self._runner = runner or _run_model_selector
        self._catalog_factory = catalog_factory
        self._observability_provider = (
            observability_provider or NoOpObservabilityProvider()
        )

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
    fallback_tool_names = tuple(
        tool_names or [getattr(tool_obj, "name", "") for tool_obj in fallback_tools]
    )
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


def _select_from_compatibility_route(
    question: str,
    *,
    allowed_tool_names: Sequence[str],
    reason_code: str,
    route_filter: Callable[[object], bool] | None = None,
) -> HybridToolSelection | None:
    route = route_public_compatibility_query(question)
    if not route.confident or route.tool_name not in allowed_tool_names:
        return None
    if route_filter is not None and not route_filter(route):
        return None
    if route.tool_name is None:
        return None
    return _build_named_candidate_selection([route.tool_name], reason_code=reason_code)


def _select_with_heuristics(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> HybridToolSelection | None:
    if not _is_elected_contact_query(question, history=history):
        salary_history_selection = _select_salary_history_with_router(question)
        if salary_history_selection is not None:
            return salary_history_selection
        spend_selection = _select_broad_spend_query(question)
        if spend_selection is not None:
            return spend_selection
        emenda_selection = _select_emenda_query_with_router(question)
        if emenda_selection is not None:
            return emenda_selection
        contract_ranking_selection = _select_contract_value_ranking_with_router(
            question
        )
        if contract_ranking_selection is not None:
            return contract_ranking_selection
        estoques_selection = _select_estoques_query_with_router(question)
        if estoques_selection is not None:
            return estoques_selection
        return None

    return _build_named_candidate_selection(
        [
            "consultar_eleitos",
            "consultar_conhecimento_municipal",
        ],
        reason_code="heuristic_elected_contacts",
    )


def _select_salary_history_with_router(
    question: str,
) -> HybridToolSelection | None:
    return _select_from_compatibility_route(
        question,
        allowed_tool_names=("buscar_historico_de_pagamentos_do_servidor",),
        reason_code="heuristic_salary_history_query",
    )


def _select_event_spend_query(
    question: str,
) -> HybridToolSelection | None:
    normalized_question = normalize_conversation_text(question)
    if not normalized_question:
        return None
    if not any(signal in normalized_question for signal in _EVENT_SPEND_SIGNAL_TERMS):
        return None
    if _extract_licitacoes_objeto(normalized_question) is None:
        return None

    return _build_named_candidate_selection(
        [
            "consultar_licitacoes",
            "consultar_contratos",
            "consultar_despesas",
        ],
        reason_code="heuristic_event_spend_query",
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

    route = route_public_compatibility_query(question)
    direct_domain_candidate_names = _select_direct_spend_candidate_names(
        normalized_question,
        route_tool_name=route.tool_name if route.confident else None,
    )
    if direct_domain_candidate_names is None:
        return None

    return _build_named_candidate_selection(
        direct_domain_candidate_names,
        reason_code="heuristic_broad_spend_query",
    )


def _strip_despesas_por_funcao_domain_keywords(normalized_question: str) -> str:
    stripped = normalized_question
    for keyword in DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS:
        stripped = stripped.replace(keyword, " ")
    return " ".join(stripped.split())


def _is_explicit_aggregate_spend_request(normalized_question: str) -> bool:
    aggregate_text = _strip_despesas_por_funcao_domain_keywords(normalized_question)
    if any(term in aggregate_text for term in _SPEND_GROUPING_TERMS):
        return True
    return any(term in aggregate_text for term in _SPEND_AGGREGATION_TERMS)


def _select_direct_spend_candidate_names(
    normalized_question: str,
    *,
    route_tool_name: str | None,
) -> list[str] | None:
    if _has_any_term(normalized_question, DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS):
        return ["consultar_despesas_por_funcao"]
    if _has_any_term(normalized_question, DIARIAS_DOMAIN_KEYWORDS):
        return ["consultar_diarias"]
    if _has_any_term(normalized_question, PASSAGENS_DOMAIN_KEYWORDS):
        return ["consultar_passagens"]
    if _has_any_term(normalized_question, DESPESAS_DOMAIN_KEYWORDS):
        return ["consultar_despesas"]
    if route_tool_name == "consultar_despesas_por_funcao":
        return ["consultar_despesas_por_funcao"]
    if route_tool_name == "consultar_diarias":
        return ["consultar_diarias"]
    if route_tool_name == "consultar_passagens":
        return ["consultar_passagens"]
    if route_tool_name == "consultar_despesas":
        return ["consultar_despesas"]
    if route_tool_name == "agregar_despesas_por_funcao":
        return ["consultar_despesas_por_funcao"]
    if route_tool_name == "agregar_diarias":
        return ["consultar_diarias"]
    if route_tool_name == "agregar_passagens":
        return ["consultar_passagens"]
    if route_tool_name == "agregar_despesas":
        return ["consultar_despesas"]
    if (
        "prefeitura gastou" in normalized_question
        or "valor gasto" in normalized_question
    ):
        return ["consultar_despesas"]
    return None


def _select_emenda_query_with_router(
    question: str,
) -> HybridToolSelection | None:
    return _select_from_compatibility_route(
        question,
        allowed_tool_names=(
            "agregar_transferencias_financeiras",
            "consultar_transferencias_financeiras",
        ),
        reason_code="heuristic_emenda_query",
        route_filter=_route_has_emenda_filter,
    )


def _select_contract_value_ranking_with_router(
    question: str,
) -> HybridToolSelection | None:
    return _select_from_compatibility_route(
        question,
        allowed_tool_names=("consultar_contratos",),
        reason_code="heuristic_contract_value_ranking",
        route_filter=lambda route: route.tool_kwargs.get("ordenar_por") == "valor",
    )


def _select_estoques_query_with_router(
    question: str,
) -> HybridToolSelection | None:
    return _select_from_compatibility_route(
        question,
        allowed_tool_names=(
            "agregar_estoques",
            "consultar_estoques",
            "consultar_movimentacoes_de_estoque",
        ),
        reason_code="heuristic_estoques_query",
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
            return HybridSelectorDecisionPayload.model_validate(
                raw_decision.model_dump()
            )
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


def _route_has_emenda_filter(route: object) -> bool:
    filtros = getattr(route, "tool_kwargs", {}).get("filtros", {})
    return isinstance(filtros, dict) and filtros.get("tipo_registro") == "emenda"


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
