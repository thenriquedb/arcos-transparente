"""Normalizadores compartilhados para colecoes aninhadas de ingestao."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


SchemaT = TypeVar("SchemaT", bound=BaseModel)


def normalize_validated_list(
    value: Any,
    *,
    schema_type: type[SchemaT],
    field_name: str,
) -> list[SchemaT]:
    """Valida uma lista aninhada descartando filhos invalidos sem falhar o pai."""

    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} deve ser uma lista")

    validated_items: list[SchemaT] = []
    for item in value:
        try:
            validated_items.append(schema_type.model_validate(item))
        except ValidationError:
            continue
    return validated_items
