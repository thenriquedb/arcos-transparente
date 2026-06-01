"""Utilitarios compartilhados de validacao e saneamento."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .text import normalize_search_text


MONTH_NAME_TO_NUMBER = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def clean_text(value: Any) -> str | None:
    """Normaliza valores textuais, removendo espacos e vazios."""

    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, (int, float, Decimal)):
        value = str(value).strip()
        return value or None
    raise ValueError("valor textual invalido")


def parse_decimal(value: Any) -> Decimal | None:
    """Converte strings monetarias e numericas para Decimal."""

    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))

    text = clean_text(value)
    if text is None:
        return None

    normalized = text.replace("R$", "").replace(" ", "")
    normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("valor decimal invalido") from exc


def parse_number(value: Any) -> Decimal | None:
    """Converte numeros gerais preservando ponto decimal quando nao ha virgula."""

    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))

    text = clean_text(value)
    if text is None:
        return None

    normalized = text.replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("valor numerico invalido") from exc


def parse_date(value: Any) -> date | None:
    """Converte datas em `dd/mm/yyyy`, ISO ou datetime para `date`."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = clean_text(value)
    if text is None:
        return None

    if "/" in text:
        try:
            dd, mm, yyyy = text.split("/")
            return date(int(yyyy), int(mm), int(dd))
        except ValueError as exc:
            raise ValueError("data invalida no formato dd/mm/yyyy") from exc

    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError as exc:
            raise ValueError("data invalida") from exc


def parse_int(value: Any) -> int | None:
    """Converte texto saneado em inteiro, preservando vazio como `None`."""

    text = clean_text(value)
    if text is None:
        return None
    return int(text)


def parse_competencia_as_date(value: Any) -> date | None:
    """Converte competencia `mm/yyyy` para o primeiro dia do mes."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = clean_text(value)
    if text is None:
        return None

    if "/" in text:
        try:
            mm, yyyy = text.split("/")
            return date(int(yyyy), int(mm), 1)
        except ValueError as exc:
            raise ValueError("competencia invalida no formato mm/yyyy") from exc

    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("data invalida") from exc


def parse_month(value: Any) -> int | None:
    """Converte numeros ou nomes de mes para o indice `1-12`."""

    if value is None:
        return None
    if isinstance(value, int):
        return value

    text = clean_text(value)
    if text is None:
        return None
    if text.isdigit():
        return int(text)
    return MONTH_NAME_TO_NUMBER.get(normalize_search_text(text))


def normalize_limit(value: Any, minimum: int = 1, maximum: int = 50) -> int:
    """Converte e limita um valor inteiro entre minimo e maximo."""

    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limite invalido") from exc
    return max(minimum, min(limit, maximum))


def validate_date_period(data_inicio: date, data_fim: date) -> None:
    """Valida que a data inicial nao seja maior que a final."""

    if data_inicio > data_fim:
        raise ValueError("data_inicio deve ser menor ou igual a data_fim")
