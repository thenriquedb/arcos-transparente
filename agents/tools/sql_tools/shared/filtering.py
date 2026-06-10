"""Motor declarativo de filtros em memória para as tools públicas de consulta.

Cada domínio descreve seus filtros como uma sequência de `FilterCondition`
(parâmetro do schema → predicado sobre a linha) em vez de repetir cadeias de
`if filtros.x:` por tool. `apply_declared_filters` aplica as condições ativas
na ordem declarada.

Convenções de ativação espelham o comportamento histórico das tools:
filtros textuais/equality são aplicados quando o valor é truthy; filtros de
faixa numérica/data quando o valor não é None.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from shared.utils.text import matches_text_query

RowGetter = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class FilterCondition:
    """Liga um parâmetro do schema de filtros a um predicado sobre a linha."""

    param: str
    predicate: Callable[[Any, Any], bool]
    activate_when_none: bool = False

    def is_active(self, value: Any) -> bool:
        if self.activate_when_none:
            return value is not None
        return bool(value)


def apply_declared_filters(
    rows: list[Any],
    filtros: Any,
    conditions: Sequence[FilterCondition],
) -> list[Any]:
    """Aplica as condições ativas (na ordem declarada) sobre as linhas."""

    for condition in conditions:
        value = getattr(filtros, condition.param)
        if condition.is_active(value):
            rows = [row for row in rows if condition.predicate(row, value)]
    return rows


def text_filter(param: str, getter: RowGetter) -> FilterCondition:
    """Filtro textual normalizado (`matches_text_query`), ativo quando truthy."""

    return FilterCondition(
        param=param,
        predicate=lambda row, value: matches_text_query(getter(row), value),
    )


def equals_filter(param: str, getter: RowGetter) -> FilterCondition:
    """Filtro de igualdade exata, ativo quando truthy."""

    return FilterCondition(
        param=param,
        predicate=lambda row, value: getter(row) == value,
    )


def min_filter(
    param: str,
    getter: RowGetter,
    *,
    default: Any = Decimal("0"),
) -> FilterCondition:
    """Limite inferior inclusivo, ativo quando o valor não é None."""

    return FilterCondition(
        param=param,
        predicate=lambda row, value: (getter(row) or default) >= value,
        activate_when_none=True,
    )


def max_filter(
    param: str,
    getter: RowGetter,
    *,
    default: Any = Decimal("0"),
) -> FilterCondition:
    """Limite superior inclusivo, ativo quando o valor não é None."""

    return FilterCondition(
        param=param,
        predicate=lambda row, value: (getter(row) or default) <= value,
        activate_when_none=True,
    )


def predicate_filter(
    param: str,
    predicate: Callable[[Any, Any], bool],
    *,
    activate_when_none: bool = False,
) -> FilterCondition:
    """Condição customizada para casos que não cabem nas fábricas padrão."""

    return FilterCondition(
        param=param,
        predicate=predicate,
        activate_when_none=activate_when_none,
    )
