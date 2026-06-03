"""Politica deterministica executada antes da selecao hibrida de tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any, Literal, Protocol

from agents.guardrails import evaluate_public_query_guardrails
from agents.routing.extractors import _normalize

PolicyAction = Literal["allow", "block", "clarify"]

_PROTECTED_ACRONYMS = {
    "UPA": "Unidade de Pronto Atendimento",
    "UBS": "Unidade Basica de Saude",
    "PSF": "Programa Saude da Familia",
    "CRAS": "Centro de Referencia de Assistencia Social",
    "CREAS": "Centro de Referencia Especializado de Assistencia Social",
}
_CONFIRMATION_TOKENS = frozenset(
    {
        "sim",
        "isso",
        "isso mesmo",
        "exato",
        "correto",
        "confirmo",
        "confirmado",
        "pode ser",
        "pode",
    }
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

    prior_user_queries = tuple(
        message.content for message in history if message.role == "user"
    )
    prior_messages = tuple(
        (
            message.role,
            message.content,
            bool(message.metadata.get("guardrail_triggered")),
        )
        for message in history
    )
    guardrail = evaluate_public_query_guardrails(
        question,
        has_history=bool(history),
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

    if reply_resolution := _resolve_pending_protected_acronym_reply(
        question,
        history=history,
    ):
        return reply_resolution

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


def _resolve_pending_protected_acronym_reply(
    question: str,
    *,
    history: Sequence[HistoryMessage],
) -> DeterministicPolicyDecision | None:
    pending = _latest_pending_protected_acronym(history)
    if pending is None:
        return None

    normalized_reply = _normalize(question)
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


def _reply_confirms_protected_acronym(
    normalized_reply: str,
    *,
    acronym: str,
    expansion: str,
) -> bool:
    if normalized_reply in _CONFIRMATION_TOKENS:
        return True
    if not normalized_reply:
        return False

    normalized_expansion = _normalize(expansion)
    acronym_pattern = re.compile(rf"\b{re.escape(acronym.lower())}\b")
    return normalized_expansion in normalized_reply or (
        acronym_pattern.search(normalized_reply) is not None
    )


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
    normalized_question = _normalize(question)
    for acronym, expansion in _PROTECTED_ACRONYMS.items():
        acronym_pattern = re.compile(rf"\b{re.escape(acronym.lower())}\b")
        if acronym_pattern.search(normalized_question) is None:
            continue
        if acronym in confirmed_acronyms:
            continue
        if _normalize(expansion) in normalized_question:
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
