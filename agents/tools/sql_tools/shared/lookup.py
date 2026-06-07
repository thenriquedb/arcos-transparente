"""Shared lookup query shapes for public SQL tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select


RowT = TypeVar("RowT")
MetadataT = TypeVar("MetadataT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


@dataclass(frozen=True)
class LookupExecutionResult:
    """Normalized lookup result before response shaping."""

    total: int
    rows: Sequence[Any]
    metadata_updates: Mapping[str, Any] = field(default_factory=dict)
    response_updates: Mapping[str, Any] = field(default_factory=dict)
    messages: Sequence[str | None] = field(default_factory=tuple)
    suggestion: str | None = None


def compose_message(messages: Sequence[str | None]) -> str | None:
    filtered = [message.strip() for message in messages if message and message.strip()]
    if not filtered:
        return None
    return " ".join(filtered)


def execute_statement_lookup(
    session,
    *,
    stmt,
    ordenar_por: str,
    ordem: str,
    offset: int,
    limite: int,
    order_columns: Mapping[str, Any],
    tie_breakers: Sequence[Any] = (),
    load_rows: Callable[[Any, Any], Sequence[RowT]],
) -> tuple[int, list[RowT]]:
    """Run a paginated statement-backed lookup with shared ordering semantics."""

    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()

    ordered_stmt = stmt.order_by(
        order_columns[ordenar_por].desc()
        if ordem == "desc"
        else order_columns[ordenar_por].asc(),
        *tie_breakers,
    )
    rows = list(load_rows(session, ordered_stmt.offset(offset).limit(limite)))
    return total, rows


def execute_collection_lookup(
    rows: Sequence[RowT],
    *,
    ordenar_por: str,
    ordem: str,
    offset: int,
    limite: int,
    sort_key_getters: Mapping[str, Callable[[RowT], Any]],
    tie_breaker_getters: Sequence[Callable[[RowT], Any]] = (),
) -> tuple[int, list[RowT]]:
    """Run a paginated collection-backed lookup with shared ordering semantics."""

    ordered = sorted(
        rows,
        key=lambda row: (
            sort_key_getters[ordenar_por](row),
            *(getter(row) for getter in tie_breaker_getters),
        ),
        reverse=ordem == "desc",
    )
    total = len(ordered)
    return total, ordered[offset : offset + limite]


def build_lookup_response(
    *,
    response_type: type[ResponseT],
    metadata: MetadataT,
    execution: LookupExecutionResult,
    project_row: Callable[[Any, list[str]], dict[str, Any]],
    campos: list[str],
    transform_results: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
    | None = None,
    pagination_message_builder: Callable[[int, int], str] | None = None,
) -> dict[str, Any]:
    """Shape a normalized lookup result into the public response envelope."""

    messages = list(execution.messages)
    response_payload = dict(execution.response_updates)
    if not execution.rows:
        return response_type(
            total=0,
            resultados=[],
            metadata=metadata,
            mensagem=compose_message(messages),
            sugestao=execution.suggestion,
            **response_payload,
        ).model_dump(mode="json")

    resultados = [project_row(row, campos) for row in execution.rows]
    if transform_results is not None:
        resultados = transform_results(resultados)

    offset = getattr(metadata, "offset", 0) or 0
    if execution.total > offset + len(resultados):
        message_builder = pagination_message_builder or (
            lambda shown, total: f"Mostrando {shown} de {total} registros encontrados."
        )
        messages.append(message_builder(len(resultados), execution.total))

    return response_type(
        total=execution.total,
        resultados=resultados,
        metadata=metadata,
        mensagem=compose_message(messages),
        sugestao=execution.suggestion,
        **response_payload,
    ).model_dump(mode="json")
