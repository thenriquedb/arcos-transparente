"""Shared aggregate query shapes for public SQL tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select

from .lookup import compose_message


RowT = TypeVar("RowT")
MetadataT = TypeVar("MetadataT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)
ItemModelT = TypeVar("ItemModelT", bound=BaseModel)


@dataclass(frozen=True)
class AggregateExecutionResult:
    """Normalized aggregate result before response shaping."""

    total_grupos: int = 0
    rows: Sequence[tuple[Any, Any]] = field(default_factory=tuple)
    valor_total: Any = None
    source_count: int | None = None
    messages: Sequence[str | None] = field(default_factory=tuple)
    suggestion: str | None = None


def execute_statement_total(
    session,
    *,
    count_stmt,
    value_stmt,
) -> tuple[int, Any]:
    """Run a statement-backed total aggregation and a matching count."""

    total_match = session.execute(count_stmt).scalar_one()
    valor_total = session.execute(value_stmt).scalar_one()
    return total_match, valor_total


def execute_statement_grouped(
    session,
    *,
    grouped_stmt,
    ordenar_por: str,
    ordem: str,
    limite: int,
    group_column,
    metric_expression,
) -> tuple[int, list[tuple[Any, Any]]]:
    """Run a grouped statement-backed aggregation with shared ordering semantics."""

    total_grupos = session.execute(
        select(func.count()).select_from(grouped_stmt.order_by(None).subquery())
    ).scalar_one()

    order_column = metric_expression if ordenar_por == "metrica" else group_column
    ordered_stmt = grouped_stmt.order_by(
        order_column.desc() if ordem == "desc" else order_column.asc()
    ).limit(limite)
    rows = list(session.execute(ordered_stmt).all())
    return total_grupos, rows


def calculate_collection_metric(
    rows: Sequence[RowT],
    *,
    metrica: str,
    metric_getters: Mapping[str, Callable[[RowT], Any]],
) -> Any:
    """Calculate a collection-backed metric using the shared count/sum contract."""

    if metrica == "contagem":
        return len(rows)

    total = 0
    for row in rows:
        total += metric_getters[metrica](row) or 0
    return total


def execute_collection_aggregate(
    rows: Sequence[RowT],
    *,
    agrupar_por: str | None,
    metrica: str,
    ordenar_por: str,
    ordem: str,
    limite: int,
    group_key_getters: Mapping[str, Callable[[RowT], Any]],
    metric_getters: Mapping[str, Callable[[RowT], Any]],
    serialize_metric: Callable[[Any], Any],
) -> AggregateExecutionResult:
    """Run a collection-backed aggregate with shared grouping and ordering semantics."""

    if agrupar_por is None:
        return AggregateExecutionResult(
            source_count=len(rows),
            valor_total=serialize_metric(
                calculate_collection_metric(
                    rows,
                    metrica=metrica,
                    metric_getters=metric_getters,
                )
            ),
        )

    grouped_rows: dict[Any, list[RowT]] = {}
    group_getter = group_key_getters[agrupar_por]
    for row in rows:
        group_value = group_getter(row)
        if group_value in (None, ""):
            group_value = "nao_informado"
        grouped_rows.setdefault(group_value, []).append(row)

    resultados = [
        (
            group_value,
            serialize_metric(
                calculate_collection_metric(
                    group_rows,
                    metrica=metrica,
                    metric_getters=metric_getters,
                )
            ),
        )
        for group_value, group_rows in grouped_rows.items()
    ]

    reverse = ordem == "desc"
    if ordenar_por == "metrica":
        resultados.sort(key=lambda item: item[1], reverse=reverse)
    else:
        resultados.sort(key=lambda item: item[0], reverse=reverse)

    total_grupos = len(resultados)
    return AggregateExecutionResult(
        total_grupos=total_grupos,
        rows=resultados[:limite],
        source_count=len(rows),
    )


def _build_total_only_message(source_count: int) -> str:
    registro_label = "registro" if source_count == 1 else "registros"
    verb_label = "correspondeu" if source_count == 1 else "corresponderam"
    return (
        "Agregacao sem agrupamento: `valor_total` e o resultado final; "
        "`resultados` vazio e `total_grupos` 0 sao esperados. "
        f"{source_count} {registro_label} {verb_label} aos filtros."
    )


def build_aggregate_response(
    *,
    response_type: type[ResponseT],
    metadata: MetadataT,
    execution: AggregateExecutionResult,
    item_model: type[ItemModelT] | None = None,
    project_group: Callable[[Any, Any, str, str], dict[str, Any]] | None = None,
    agrupar_por: str | None = None,
    metrica: str | None = None,
    serialize_group_value: Callable[[Any], Any] = lambda value: value,
    serialize_metric: Callable[[Any], Any] = lambda value: value,
) -> dict[str, Any]:
    """Shape a normalized aggregate result into the public response envelope."""

    messages = list(execution.messages)

    if agrupar_por is None:
        if execution.source_count is not None and execution.source_count > 0:
            messages.append(_build_total_only_message(execution.source_count))
        return response_type(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=execution.valor_total,
            mensagem=compose_message(messages),
            sugestao=execution.suggestion,
        ).model_dump(mode="json")

    if not execution.rows:
        return response_type(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            mensagem=compose_message(messages),
            sugestao=execution.suggestion,
        ).model_dump(mode="json")

    assert metrica is not None

    if project_group is not None:
        resultados = [
            project_group(
                serialize_group_value(group_value),
                serialize_metric(metric_value),
                agrupar_por,
                metrica,
            )
            for group_value, metric_value in execution.rows
        ]
    else:
        assert item_model is not None
        resultados = [
            item_model.model_validate(
                {
                    agrupar_por: serialize_group_value(group_value),
                    metrica: serialize_metric(metric_value),
                }
            ).model_dump(mode="json", exclude_none=True)
            for group_value, metric_value in execution.rows
        ]
    if execution.total_grupos > len(resultados):
        messages.append(
            f"Mostrando {len(resultados)} de {execution.total_grupos} grupos encontrados."
        )

    return response_type(
        total_grupos=execution.total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=compose_message(messages),
        sugestao=execution.suggestion,
    ).model_dump(mode="json")
