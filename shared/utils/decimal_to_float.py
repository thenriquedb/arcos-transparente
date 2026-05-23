from decimal import Decimal


def decimal_to_float(valor: Decimal | None) -> float | None:
    if valor is None:
        return None

    return float(valor)
