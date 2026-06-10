"""Conversões de Decimal para tipos serializáveis em JSON."""

from decimal import Decimal


def decimal_to_float(valor: Decimal | None) -> float | None:
    """Converte um Decimal opcional em float, preservando None."""

    if valor is None:
        return None

    return float(valor)


def decimal_or_int_to_json(value: Decimal | int | None) -> float | int | None:
    """Serializa métricas que podem ser contagem (int) ou soma (Decimal)."""

    if isinstance(value, Decimal):
        return decimal_to_float(value)
    return value
