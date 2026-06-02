"""Tool publica para agregacoes de transferencias financeiras."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager

from .agregar_transferencias_financeiras_schema import (
    AgregarTransferenciasFinanceirasMetadata,
    AgregarTransferenciasFinanceirasParams,
    AgregarTransferenciasFinanceirasResponse,
)
from .consultar_transferencias_financeiras_query import (
    load_filtered_transferencias_financeiras,
)


def _metric(registros: list[dict[str, Any]], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    if metrica == "soma_programacao_inicial":
        return sum(
            Decimal(str(registro.get("programacao_inicial") or 0))
            for registro in registros
        )
    return sum(Decimal(str(registro.get("valor") or 0)) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


@register(
    name="agregar_transferencias_financeiras",
    scope=PUBLIC_SCOPE,
    tags=["domain:transferencias_financeiras", "shape:aggregate"],
)
def agregar_transferencias_financeiras(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre transferencias e emendas.

    Use esta tool quando a pergunta pedir total transferido, total recebido,
    quantidade de registros ou rankings por unidade, tipo de movimento, autor,
    funcao ou tipo de emenda.
    NAO use para listar registros individuais; para isso use
    `consultar_transferencias_financeiras`.
    """
    try:
        params = AgregarTransferenciasFinanceirasParams.model_validate(
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
        fallback_metadata = AgregarTransferenciasFinanceirasMetadata(
            metrica="soma_valor",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarTransferenciasFinanceirasResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_transferencias_financeiras(session, params.filtros)

    metadata = AgregarTransferenciasFinanceirasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    if params.agrupar_por is None:
        valor_total = _metric_to_json(_metric(registros, params.metrica))
        return AgregarTransferenciasFinanceirasResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhum registro de transferencias financeiras encontrado com os filtros."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grupos: dict[str, list[dict[str, Any]]] = {}
    for registro in registros:
        valor = registro.get(params.agrupar_por) or "nao_informado"
        grupos.setdefault(str(valor), []).append(registro)

    resultados = []
    for valor_grupo, linhas in grupos.items():
        resultados.append(
            {
                params.agrupar_por: valor_grupo,
                params.metrica: _metric_to_json(_metric(linhas, params.metrica)),
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

    return AgregarTransferenciasFinanceirasResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhum registro de transferencias financeiras encontrado com os filtros."
            if not resultados
            else None
        ),
    ).model_dump(mode="json")
