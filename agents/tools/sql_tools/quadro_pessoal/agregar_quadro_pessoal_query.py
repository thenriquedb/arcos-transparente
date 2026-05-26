"""Tool publica para agregacoes do quadro de pessoal."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import QuadroPessoal

from .agregar_quadro_pessoal_schema import (
    AgregarQuadroPessoalMetadata,
    AgregarQuadroPessoalParams,
    AgregarQuadroPessoalResponse,
)
from .consultar_quadro_pessoal_query import load_filtered_quadro_pessoal


def _metric(registros: list[QuadroPessoal], metrica: str) -> int:
    if metrica == "contagem":
        return len(registros)
    if metrica == "soma_vagas_criadas":
        return sum(registro.vagas_criadas or 0 for registro in registros)
    if metrica == "soma_vagas_preenchidas":
        return sum(registro.vagas_preenchidas or 0 for registro in registros)
    return sum(
        (registro.vagas_criadas or 0) - (registro.vagas_preenchidas or 0)
        for registro in registros
    )


def _group_value(registro: QuadroPessoal, group: str) -> str | int:
    mapping = {
        "origem": registro.origem,
        "regime": registro.regime_contratacao,
        "mes": registro.competencia_referencia.month,
    }
    return mapping[group]


@register(
    name="agregar_quadro_pessoal",
    scope=PUBLIC_SCOPE,
    tags=["domain:quadro_pessoal", "shape:aggregate"],
)
def agregar_quadro_pessoal(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_vagas_preenchidas",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais e rankings sobre vagas do quadro de pessoal.

    Use esta tool quando a pergunta pedir quantas vagas existem, quantas foram
    preenchidas ou qual regime, origem ou mes concentra mais vagas.
    NAO use para listar registros individuais do quadro de pessoal; para isso use
    `consultar_quadro_pessoal`.
    NAO use para contar pessoas da folha ou listar servidores; para isso use
    `agregar_servidores` ou `consultar_servidores`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `origem`, `ano`,
            `mes` e `regime`.
        agrupar_por: Campo opcional de agrupamento. Aceita `origem`, `regime`
            ou `mes`. Se nao for informado, a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_vagas_criadas`,
            `soma_vagas_preenchidas` ou `saldo_vagas`.
        ordenar_por: Aceita `metrica` ou o mesmo valor usado em `agrupar_por`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos retornados. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos; cada item traz o campo de agrupamento e a
          metrica calculada.
        - `metadata`: filtros aplicados e configuracao da agregacao.
        - `valor_total`: valor agregado quando `agrupar_por` nao for informado.
        - `mensagem`: aviso quando so parte dos grupos for exibida.
        - `sugestao`: dica quando nenhum registro corresponder aos filtros.
    """
    try:
        params = AgregarQuadroPessoalParams.model_validate(
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
        fallback_metadata = AgregarQuadroPessoalMetadata(
            metrica="soma_vagas_preenchidas",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarQuadroPessoalResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_quadro_pessoal(session, params.filtros)

    metadata = AgregarQuadroPessoalMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    if params.agrupar_por is None:
        valor_total = _metric(registros, params.metrica)
        return AgregarQuadroPessoalResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhum registro de quadro de pessoal encontrado."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grupos: dict[str, list[QuadroPessoal]] = {}
    for registro in registros:
        valor = _group_value(registro, params.agrupar_por)
        grupos.setdefault(str(valor), []).append(registro)

    resultados = []
    for group_value, group_rows in grupos.items():
        resultados.append(
            {
                params.agrupar_por: group_value,
                params.metrica: _metric(group_rows, params.metrica),
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

    return AgregarQuadroPessoalResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhum registro de quadro de pessoal encontrado."
            if not resultados
            else None
        ),
    ).model_dump(mode="json")
