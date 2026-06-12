"""Helpers compartilhados para projeção de campos públicos nas SQL tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, TypeVar


RowT = TypeVar("RowT")
ProjectionOrder = Literal["payload", "requested"]


def project_public_dict(
    payload: Mapping[str, Any],
    campos: list[str] | None,
    *,
    default_fields: Sequence[str] | None = None,
    order: ProjectionOrder = "payload",
) -> dict[str, Any]:
    """Seleciona campos públicos preservando a ordem atual esperada pelo caller."""

    if campos:
        if order == "requested":
            return {campo: payload[campo] for campo in campos if campo in payload}
        selected = set(campos)
        return {campo: valor for campo, valor in payload.items() if campo in selected}

    if default_fields is None:
        return dict(payload)

    if order == "requested":
        return {campo: payload[campo] for campo in default_fields if campo in payload}
    selected = set(default_fields)
    return {campo: valor for campo, valor in payload.items() if campo in selected}


def project_public_fields(
    registro: RowT,
    campos: list[str] | None,
    *,
    serializer: Callable[[RowT], Mapping[str, Any]],
    default_fields: Sequence[str] | None = None,
    order: ProjectionOrder = "payload",
) -> dict[str, Any]:
    """Serializa um registro e aplica a seleção de campos públicos."""

    return project_public_dict(
        serializer(registro),
        campos,
        default_fields=default_fields,
        order=order,
    )


def project_public_rows(
    registros: Sequence[RowT],
    campos: list[str] | None,
    *,
    serializer: Callable[[RowT], Mapping[str, Any]],
    default_fields: Sequence[str] | None = None,
    order: ProjectionOrder = "payload",
) -> list[dict[str, Any]]:
    """Projeta uma coleção de registros usando o mesmo contrato de campos."""

    return [
        project_public_fields(
            registro,
            campos,
            serializer=serializer,
            default_fields=default_fields,
            order=order,
        )
        for registro in registros
    ]
