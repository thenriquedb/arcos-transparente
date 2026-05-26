"""Tool publica para agregacoes de patrimonio."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Patrimonio

from .agregar_patrimonios_schema import (
    AgregarPatrimoniosMetadata,
    AgregarPatrimoniosParams,
    AgregarPatrimoniosResponse,
)
from .consultar_patrimonios_query import load_filtered_patrimonios


def _metric(registros: list[Patrimonio], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field = {
        "soma_valor_atualizado": "valor_atualizado",
        "soma_valor_ingresso": "valor_ingresso",
    }[metrica]
    return sum((getattr(registro, field) or Decimal("0")) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    return float(value) if isinstance(value, Decimal) else value


def _group_value(registro: Patrimonio, group: str) -> str | None:
    mapping = {
        "unidade_responsavel": registro.unidade_gestora,
        "localizacao": registro.localizacao,
        "status": registro.status,
        "situacao": registro.situacao_bem,
        "tipo_ingresso": registro.tipo_ingresso,
        "classificacao": registro.classificacao,
    }
    return mapping[group]


@register(
    name="agregar_patrimonios",
    scope=PUBLIC_SCOPE,
    tags=["domain:patrimonios", "shape:aggregate"],
)
def agregar_patrimonios(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Agrega bens patrimoniais por localização, status, classificação ou origem.

    Use para totais de bens, rankings de locais com mais patrimônio e somas de
    valor atualizado ou de ingresso.
    """
    try:
        params = AgregarPatrimoniosParams.model_validate(
            {
                "filtros": filtros,
                "agrupar_por": agrupar_por,
                "metrica": metrica,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
            }
        )
    except ValidationError as exc:
        fallback_metadata = AgregarPatrimoniosMetadata(
            metrica="contagem",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarPatrimoniosResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_patrimonios(session, params.filtros)

    metadata = AgregarPatrimoniosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    if params.agrupar_por is None:
        valor_total = _metric_to_json(_metric(registros, params.metrica))
        return AgregarPatrimoniosResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhum bem patrimonial encontrado com os filtros."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grupos: dict[str, list[Patrimonio]] = {}
    for registro in registros:
        valor = _group_value(registro, params.agrupar_por) or "nao_informado"
        grupos.setdefault(str(valor), []).append(registro)

    resultados = []
    for group_value, group_rows in grupos.items():
        resultados.append(
            {
                params.agrupar_por: group_value,
                params.metrica: _metric_to_json(_metric(group_rows, params.metrica)),
            }
        )

    reverse = params.ordem == "desc"
    if params.ordenar_por == "metrica":
        resultados.sort(key=lambda item: item[params.metrica], reverse=reverse)
    else:
        resultados.sort(key=lambda item: item[params.agrupar_por], reverse=reverse)

    total_grupos = len(resultados)
    resultados = resultados[: params.limite]
    mensagem = None
    if total_grupos > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."

    return AgregarPatrimoniosResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhum bem patrimonial encontrado com os filtros."
            if not resultados
            else None
        ),
    ).model_dump(mode="json")
