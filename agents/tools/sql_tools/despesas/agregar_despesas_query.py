"""Tool publica para agregacoes de despesas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import DespesaDocumento

from .agregar_despesas_schema import (
    AgregarDespesasMetadata,
    AgregarDespesasParams,
    AgregarDespesasResponse,
)
from .consultar_despesas_query import load_filtered_despesas


def _decimal_to_json(value: Decimal) -> float:
    return float(value)


def _metric(registros: list[DespesaDocumento], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field_by_metric = {
        "soma_valor_documento": "valor_documento",
        "soma_valor_empenhado": "valor_empenhado",
        "soma_valor_pago": "valor_pago",
        "soma_valor_anulado": "valor_anulado",
    }
    field = field_by_metric[metrica]
    return sum((getattr(registro, field) or Decimal("0")) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return _decimal_to_json(value)
    return value


def _group_value(registro: DespesaDocumento, group: str) -> str | int | None:
    mapping = {
        "tipo": registro.tipo_origem,
        "origem": registro.origem,
        "ano": registro.exercicio,
        "mes": registro.data_documento.month,
        "unidade_responsavel": registro.unidade_gestora,
        "area": registro.funcao,
        "credor": registro.credor,
        "conta_extra": registro.conta_extra_descricao,
    }
    return mapping[group]


@register(
    name="agregar_despesas",
    scope=PUBLIC_SCOPE,
    tags=["domain:despesas", "shape:aggregate"],
)
def agregar_despesas(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_pago",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre documentos de despesa.

    Use esta tool quando a pergunta pedir total pago, total empenhado, total
    anulado, maiores credores ou comparacoes por area, origem, unidade ou tipo
    de documento.
    NAO use para listar documentos individuais; para isso use
    `consultar_despesas`.
    NAO use para planejamento orcamentario; para isso use
    `agregar_planejamento`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `tipo`, `origem`,
            `ano`, `data_inicio`, `data_fim`, `numero`, `credor`, `cpf_cnpj`,
            `unidade_responsavel`, `area`, `conta_extra`, `contrato` e
            `descricao`. `tipo` aceita `empenho`, `restos_a_pagar` ou
            `documento_extra`. Datas em `YYYY-MM-DD`.
        agrupar_por: Campo opcional de agrupamento. Aceita `tipo`, `origem`,
            `ano`, `mes`, `unidade_responsavel`, `area`, `credor` ou
            `conta_extra`. Se nao for informado, a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_documento`,
            `soma_valor_empenhado`, `soma_valor_pago` ou `soma_valor_anulado`.
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
        - `sugestao`: dica quando nenhuma despesa corresponder aos filtros.
    """
    try:
        params = AgregarDespesasParams.model_validate(
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
        fallback_metadata = AgregarDespesasMetadata(
            metrica="soma_valor_pago",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarDespesasResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_despesas(session, params.filtros)

    metadata = AgregarDespesasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    if params.agrupar_por is None:
        valor_total = _metric_to_json(_metric(registros, params.metrica))
        return AgregarDespesasResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhuma despesa encontrada com os filtros."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grupos: dict[str, list[DespesaDocumento]] = {}
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

    return AgregarDespesasResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhuma despesa encontrada com os filtros." if not resultados else None
        ),
    ).model_dump(mode="json")
