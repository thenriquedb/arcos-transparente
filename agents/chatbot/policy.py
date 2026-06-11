"""Politica deterministica executada antes da selecao hibrida de tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any, Literal, Protocol

from agents.guardrails import evaluate_public_query_guardrails
from agents.routing.compatibility import route_public_compatibility_query
from agents.routing.conversation import (
    looks_like_confirmation_text,
    normalize_conversation_text,
)

PolicyAction = Literal["allow", "block", "clarify"]

_PROTECTED_ACRONYMS = {
    "UPA": "Unidade de Pronto Atendimento",
    "UBS": "Unidade Basica de Saude",
    "PSF": "Programa Saude da Familia",
    "CRAS": "Centro de Referencia de Assistencia Social",
    "CREAS": "Centro de Referencia Especializado de Assistencia Social",
    "FUMUSA": "Fundação Municipal de Saúde e Assistência",
}
_PUBLIC_CLARIFICATION_HINTS = (
    "confirma",
    "confirmar",
    "voce quer dizer",
    "quer dizer",
    "voce quis dizer",
    "quis dizer",
    "esta se referindo",
    "esta falando de",
    "se refere",
    "so para confirmar",
    "apenas para confirmar",
)
_PUBLIC_CLARIFICATION_EXCLUSION_HINTS = (
    "quer que eu faca isso",
    "quer que eu mostre",
    "quer que eu liste",
    "quer ver a lista completa",
    "deseja ver a lista completa",
)
_PUBLIC_CLARIFICATION_REPLY_STOPWORDS = frozenset(
    {
        "a",
        "as",
        "com",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "ou",
        "para",
        "por",
        "quero",
        "saber",
    }
)
_BUS_TYPE_REPLY_STEMS = (
    "intermunicip",
    "municip",
    "tarifa zero",
    "urban",
    "gratuit",
    "rodoviari",
)


class HistoryMessage(Protocol):
    role: str
    content: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DeterministicPolicyDecision:
    """Decisao pre-modelo autoritativa para o chatbot cidadao."""

    action: PolicyAction
    category: str
    message: str | None = None
    resolved_question: str | None = None
    user_metadata: dict[str, Any] = field(default_factory=dict)
    assistant_metadata: dict[str, Any] = field(default_factory=dict)


def evaluate_deterministic_policy(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> DeterministicPolicyDecision:
    """Resolve bloqueios hard-coded e clarificacoes protegidas antes do seletor."""

    prior_user_queries = tuple(message.content for message in history if message.role == "user")
    prior_messages = tuple(
        (
            message.role,
            message.content,
            bool(message.metadata.get("guardrail_triggered")),
        )
        for message in history
    )
    if reply_resolution := _resolve_pending_protected_acronym_reply(
        question,
        history=history,
    ):
        guardrail = _evaluate_guardrail_for_policy_question(
            reply_resolution.resolved_question or question,
            history=history,
            prior_user_queries=prior_user_queries,
            prior_messages=prior_messages,
        )
        if not guardrail.allowed:
            return DeterministicPolicyDecision(
                action="block",
                category=guardrail.category,
                message=guardrail.message,
                assistant_metadata={"guardrail_category": guardrail.category},
            )
        return reply_resolution

    if reply_resolution := _resolve_pending_public_clarification_reply(
        question,
        history=history,
    ):
        guardrail = _evaluate_guardrail_for_policy_question(
            reply_resolution.resolved_question or question,
            history=history,
            prior_user_queries=prior_user_queries,
            prior_messages=prior_messages,
        )
        if not guardrail.allowed:
            return DeterministicPolicyDecision(
                action="block",
                category=guardrail.category,
                message=guardrail.message,
                assistant_metadata={"guardrail_category": guardrail.category},
            )
        return reply_resolution

    guardrail = _evaluate_guardrail_for_policy_question(
        question,
        history=history,
        prior_user_queries=prior_user_queries,
        prior_messages=prior_messages,
    )
    if not guardrail.allowed:
        return DeterministicPolicyDecision(
            action="block",
            category=guardrail.category,
            message=guardrail.message,
            assistant_metadata={"guardrail_category": guardrail.category},
        )

    confirmed_acronyms = _collect_confirmed_acronyms(history)
    if pending_acronym := _detect_pending_protected_acronym(
        question,
        confirmed_acronyms=confirmed_acronyms,
    ):
        acronym, expansion = pending_acronym
        return DeterministicPolicyDecision(
            action="clarify",
            category="protected_acronym",
            message=f"Você quer dizer {acronym} como {expansion}?",
            assistant_metadata={
                "policy_action": "clarify",
                "policy_category": "protected_acronym",
                "pending_clarification": {
                    "acronym": acronym,
                    "expansion": expansion,
                    "original_question": question,
                },
            },
        )

    rewritten_question, rewritten_metadata = _rewrite_confirmed_acronyms(
        question,
        confirmed_acronyms=confirmed_acronyms,
    )
    return DeterministicPolicyDecision(
        action="allow",
        category="allowed",
        resolved_question=rewritten_question,
        user_metadata=rewritten_metadata,
    )


def _evaluate_guardrail_for_policy_question(
    question: str,
    *,
    history: Sequence[HistoryMessage],
    prior_user_queries: Sequence[str],
    prior_messages: Sequence[tuple[str, str, bool]],
):
    compatibility_route = route_public_compatibility_query(question)
    return evaluate_public_query_guardrails(
        question,
        compatibility_route=compatibility_route,
        has_history=bool(history),
        prior_user_queries=prior_user_queries,
        prior_messages=prior_messages,
    )


def _resolve_pending_protected_acronym_reply(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> DeterministicPolicyDecision | None:
    pending = _latest_pending_protected_acronym(history)
    if pending is None:
        return None

    normalized_reply = normalize_conversation_text(question)
    expansion = str(pending["expansion"])
    acronym = str(pending["acronym"])
    if not _reply_confirms_protected_acronym(
        normalized_reply,
        acronym=acronym,
        expansion=expansion,
    ):
        return None

    resolved_question = _replace_protected_acronym(
        str(pending["original_question"]),
        acronym=acronym,
        expansion=expansion,
    )
    return DeterministicPolicyDecision(
        action="allow",
        category="allowed",
        resolved_question=resolved_question,
        user_metadata={
            "confirmed_acronyms": {
                acronym: expansion,
            }
        },
        assistant_metadata={
            "policy_action": "allow",
            "policy_category": "protected_acronym_confirmation",
            "resolved_from_clarification": {
                "acronym": acronym,
                "expansion": expansion,
            },
        },
    )


def _resolve_pending_public_clarification_reply(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> DeterministicPolicyDecision | None:
    pending = _latest_pending_public_clarification(history)
    if pending is None:
        return None

    normalized_reply = normalize_conversation_text(question)
    if not looks_like_confirmation_text(normalized_reply):
        if not _looks_like_public_clarification_answer(
            normalized_reply,
            assistant_clarification=pending["assistant_clarification"],
        ):
            return None

        resolved_question = _build_public_clarification_answer_resolution(
            original_question=pending["original_question"],
            user_reply=question,
        )
        return DeterministicPolicyDecision(
            action="allow",
            category="allowed",
            resolved_question=resolved_question,
            user_metadata={
                "resolved_public_clarification": {
                    "original_question": pending["original_question"],
                    "user_reply": question,
                }
            },
            assistant_metadata={
                "policy_action": "allow",
                "policy_category": "public_clarification_answer",
                "resolved_from_clarification": {
                    "assistant_prompt": pending["assistant_clarification"],
                    "user_reply": question,
                },
            },
        )

    resolved_question = _build_public_clarification_resolution(
        original_question=pending["original_question"],
        assistant_clarification=pending["assistant_clarification"],
    )
    return DeterministicPolicyDecision(
        action="allow",
        category="allowed",
        resolved_question=resolved_question,
        user_metadata={
            "resolved_public_clarification": {
                "original_question": pending["original_question"],
            }
        },
        assistant_metadata={
            "policy_action": "allow",
            "policy_category": "public_clarification_confirmation",
            "resolved_from_clarification": {
                "assistant_prompt": pending["assistant_clarification"],
            },
        },
    )


def _latest_pending_protected_acronym(
    history: Sequence[HistoryMessage],
) -> dict[str, str] | None:
    for message in reversed(history):
        if message.role == "user" and message.content.strip():
            return None
        if message.role != "assistant":
            continue
        if bool(message.metadata.get("guardrail_triggered")):
            return None
        if message.metadata.get("policy_category") != "protected_acronym":
            continue
        pending = message.metadata.get("pending_clarification")
        if not isinstance(pending, Mapping):
            continue
        acronym = str(pending.get("acronym", "")).strip()
        expansion = str(pending.get("expansion", "")).strip()
        original_question = str(pending.get("original_question", "")).strip()
        if acronym and expansion and original_question:
            return {
                "acronym": acronym,
                "expansion": expansion,
                "original_question": original_question,
            }
    return None


def _latest_pending_public_clarification(
    history: Sequence[HistoryMessage],
) -> dict[str, str] | None:
    if not history:
        return None

    latest_message = history[-1]
    if latest_message.role != "assistant":
        return None
    if bool(latest_message.metadata.get("guardrail_triggered")):
        return None
    if latest_message.metadata.get("policy_category") == "protected_acronym":
        return None

    assistant_clarification = str(latest_message.content).strip()
    if not _looks_like_public_clarification_prompt(assistant_clarification):
        return None

    for message in reversed(history[:-1]):
        if message.role != "user":
            continue
        original_question = str(message.content).strip()
        if not original_question:
            return None
        return {
            "assistant_clarification": assistant_clarification,
            "original_question": original_question,
        }

    return None


def _reply_confirms_protected_acronym(
    normalized_reply: str,
    *,
    acronym: str,
    expansion: str,
) -> bool:
    if looks_like_confirmation_text(normalized_reply):
        return True
    if not normalized_reply:
        return False

    normalized_expansion = normalize_conversation_text(expansion)
    acronym_pattern = re.compile(rf"\b{re.escape(acronym.lower())}\b")
    return normalized_expansion in normalized_reply or (acronym_pattern.search(normalized_reply) is not None)


def _looks_like_public_clarification_prompt(content: str) -> bool:
    if "?" not in content:
        return False

    normalized_content = normalize_conversation_text(content)
    if not normalized_content:
        return False
    if any(exclusion_hint in normalized_content for exclusion_hint in _PUBLIC_CLARIFICATION_EXCLUSION_HINTS):
        return False
    if _looks_like_bus_type_clarification_prompt(normalized_content):
        return True
    return any(clarification_hint in normalized_content for clarification_hint in _PUBLIC_CLARIFICATION_HINTS)


def _looks_like_bus_type_clarification_prompt(normalized_content: str) -> bool:
    """Reconhece a pergunta que confirma o tipo de ônibus antes de buscar.

    Horário de ônibus é ambíguo entre o transporte municipal (Tarifa Zero) e o
    intermunicipal. Quando o assistente pede essa distinção, a resposta curta do
    cidadão ("intermunicipais", "tarifa zero") precisa ser resolvida aqui em vez
    de cair no guardrail de fora de escopo.
    """

    has_intermunicipal = "intermunicip" in normalized_content
    has_municipal = (
        "tarifa zero" in normalized_content
        or "urban" in normalized_content
        or re.search(r"(?<!inter)municip", normalized_content) is not None
    )
    return has_intermunicipal and has_municipal


def _looks_like_public_clarification_answer(
    normalized_reply: str,
    *,
    assistant_clarification: str,
) -> bool:
    if not normalized_reply or "?" in normalized_reply:
        return False

    reply_tokens = _content_tokens(normalized_reply)
    if not reply_tokens or len(reply_tokens) > 10:
        return False

    meaningful_reply_tokens = {token for token in reply_tokens if token not in _PUBLIC_CLARIFICATION_REPLY_STOPWORDS}
    if not meaningful_reply_tokens:
        return False

    normalized_clarification = normalize_conversation_text(assistant_clarification)
    if _looks_like_bus_type_clarification_prompt(normalized_clarification) and _reply_indicates_bus_type(
        normalized_reply
    ):
        return True

    clarification_tokens = _content_tokens(normalized_clarification)
    return any(token in clarification_tokens for token in meaningful_reply_tokens)


def _reply_indicates_bus_type(normalized_reply: str) -> bool:
    """Detecta o tipo de ônibus na resposta por radical, tolerando plural e verbo.

    O match por token exato falha em "quero os municipais" quando a pergunta usou
    "municipal"; usar radicais ("municip", "intermunicip", "tarifa zero", ...)
    resolve a preferência sem depender da forma exata.
    """

    return any(stem in normalized_reply for stem in _BUS_TYPE_REPLY_STEMS)


def _build_public_clarification_resolution(
    *,
    original_question: str,
    assistant_clarification: str,
) -> str:
    normalized_clarification = " ".join(assistant_clarification.split())
    return (
        f"{original_question}\n\n"
        "Considere a seguinte clarificacao ja confirmada pelo usuario para a "
        f"mesma pergunta: {normalized_clarification}"
    )


def _build_public_clarification_answer_resolution(
    *,
    original_question: str,
    user_reply: str,
) -> str:
    normalized_reply = " ".join(user_reply.split())
    return (
        f"{original_question}\n\n"
        "Considere a seguinte preferencia ja informada pelo usuario para a "
        f"mesma pergunta: {normalized_reply}"
    )


def _content_tokens(content: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", content)


def _collect_confirmed_acronyms(
    history: Sequence[HistoryMessage],
) -> dict[str, str]:
    confirmed: dict[str, str] = {}
    for message in history:
        mapping = message.metadata.get("confirmed_acronyms")
        if not isinstance(mapping, Mapping):
            continue
        for acronym, expansion in mapping.items():
            if not acronym or not expansion:
                continue
            confirmed[str(acronym).upper()] = str(expansion)
    return confirmed


def _detect_pending_protected_acronym(
    question: str,
    *,
    confirmed_acronyms: Mapping[str, str],
) -> tuple[str, str] | None:
    normalized_question = normalize_conversation_text(question)
    for acronym, expansion in _PROTECTED_ACRONYMS.items():
        acronym_pattern = re.compile(rf"\b{re.escape(acronym.lower())}\b")
        if acronym_pattern.search(normalized_question) is None:
            continue
        if acronym in confirmed_acronyms:
            continue
        if normalize_conversation_text(expansion) in normalized_question:
            continue
        return acronym, expansion
    return None


def _rewrite_confirmed_acronyms(
    question: str,
    *,
    confirmed_acronyms: Mapping[str, str],
) -> tuple[str, dict[str, Any]]:
    rewritten = question
    reapplied: dict[str, str] = {}
    for acronym, expansion in confirmed_acronyms.items():
        candidate = _replace_protected_acronym(
            rewritten,
            acronym=acronym,
            expansion=expansion,
        )
        if candidate == rewritten:
            continue
        rewritten = candidate
        reapplied[acronym] = expansion
    if not reapplied:
        return question, {}
    return rewritten, {"confirmed_acronyms": reapplied}


def _replace_protected_acronym(
    question: str,
    *,
    acronym: str,
    expansion: str,
) -> str:
    pattern = re.compile(rf"\b{re.escape(acronym)}\b", re.IGNORECASE)
    return pattern.sub(expansion, question)
