"""Normalizadores compartilhados entre schemas de tools SQL."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from shared.utils.validation import clean_text


SchemaT = TypeVar("SchemaT", bound=BaseModel)
FieldErrorStyle = Literal["campo", "campos"]


def normalize_model_input(
    value: Any,
    *,
    schema_type: type[SchemaT],
    field_name: str,
) -> SchemaT:
    """Normaliza um campo objeto validando-o com o schema informado."""

    if value is None:
        return schema_type()
    if isinstance(value, schema_type):
        return value
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} deve ser um objeto")
    return schema_type.model_validate(value)


def normalize_selected_fields(
    value: Any,
    *,
    allowed_fields: Collection[str],
    require_list: bool,
    error_style: FieldErrorStyle,
) -> list[str]:
    """Normaliza listas de campos preservando o estilo de erro atual do caller."""

    if value is None:
        return []
    if require_list and not isinstance(value, list):
        raise ValueError("campos deve ser uma lista")

    if error_style == "campos":
        campos = [clean_text(item) for item in value]
        invalidos = [item for item in campos if item not in allowed_fields]
        if invalidos:
            raise ValueError(f"campos nao suportados: {invalidos}")
        return [item for item in campos if item is not None]

    normalized_fields: list[str] = []
    for item in value:
        field_name = clean_text(item)
        if field_name is None:
            continue
        if field_name not in allowed_fields:
            raise ValueError(f"campo nao suportado: {field_name}")
        normalized_fields.append(field_name)
    return normalized_fields
