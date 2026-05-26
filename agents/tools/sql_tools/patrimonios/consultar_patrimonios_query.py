"""Tool publica para consultas amplas de patrimonio."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Patrimonio
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_patrimonios_schema import (
    ALLOWED_PATRIMONIO_FIELDS,
    ConsultarPatrimoniosMetadata,
    ConsultarPatrimoniosParams,
    ConsultarPatrimoniosResponse,
    PatrimonioFiltroSchema,
)


def _row_to_public_dict(registro: Patrimonio) -> dict[str, Any]:
    return {
        "unidade_responsavel": registro.unidade_gestora,
        "placa": registro.placa,
        "descricao": registro.descricao_item,
        "classificacao": registro.classificacao,
        "localizacao": registro.localizacao,
        "status": registro.status,
        "situacao": registro.situacao_bem,
        "tipo_ingresso": registro.tipo_ingresso,
        "data_aquisicao": registro.data_aquisicao.isoformat()
        if registro.data_aquisicao
        else None,
        "data_baixa": registro.data_baixa.isoformat() if registro.data_baixa else None,
        "valor_ingresso": decimal_to_float(registro.valor_ingresso),
        "valor_atualizado": decimal_to_float(registro.valor_atualizado),
    }


def load_filtered_patrimonios(
    session, filtros: PatrimonioFiltroSchema
) -> list[Patrimonio]:
    registros = session.query(Patrimonio).all()

    if filtros.unidade_responsavel:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_responsavel)
        ]
    if filtros.placa:
        registros = [r for r in registros if matches_text_query(r.placa, filtros.placa)]
    if filtros.descricao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.descricao_item, filtros.descricao)
        ]
    if filtros.classificacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.classificacao, filtros.classificacao)
        ]
    if filtros.localizacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.localizacao, filtros.localizacao)
        ]
    if filtros.status:
        registros = [
            r for r in registros if matches_text_query(r.status, filtros.status)
        ]
    if filtros.situacao:
        registros = [
            r for r in registros if matches_text_query(r.situacao_bem, filtros.situacao)
        ]
    if filtros.tipo_ingresso:
        registros = [
            r
            for r in registros
            if matches_text_query(r.tipo_ingresso, filtros.tipo_ingresso)
        ]
    if filtros.data_aquisicao_inicio:
        registros = [
            r
            for r in registros
            if r.data_aquisicao is not None
            and r.data_aquisicao >= filtros.data_aquisicao_inicio
        ]
    if filtros.data_aquisicao_fim:
        registros = [
            r
            for r in registros
            if r.data_aquisicao is not None
            and r.data_aquisicao <= filtros.data_aquisicao_fim
        ]

    return registros


def sort_patrimonios(
    registros: list[Patrimonio],
    ordenar_por: str,
    ordem: str,
) -> list[Patrimonio]:
    reverse = ordem == "desc"

    def key(registro: Patrimonio) -> Any:
        mapping = {
            "data_aquisicao": registro.data_aquisicao,
            "valor_atualizado": registro.valor_atualizado or Decimal("0"),
            "valor_ingresso": registro.valor_ingresso or Decimal("0"),
            "descricao": registro.descricao_item or "",
            "localizacao": registro.localizacao or "",
            "placa": registro.placa or "",
        }
        return mapping[ordenar_por] or ""

    return sorted(registros, key=key, reverse=reverse)


def project_patrimonios(
    registros: list[Patrimonio],
    campos: list[str],
) -> list[dict[str, Any]]:
    selected = campos or list(ALLOWED_PATRIMONIO_FIELDS)
    return [
        {
            campo: value
            for campo, value in _row_to_public_dict(registro).items()
            if campo in selected
        }
        for registro in registros
    ]


@register(
    name="consultar_patrimonios",
    scope=PUBLIC_SCOPE,
    tags=["domain:patrimonios", "shape:lookup"],
)
def consultar_patrimonios(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_aquisicao",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista bens patrimoniais por placa, descricao, localizacao, status e valor.

    Use esta tool quando a pergunta pedir quais bens existem, onde estao, qual a
    classificacao de um bem ou quais itens foram adquiridos em certo periodo.
    NAO use para totais, somas ou rankings agregados; para isso use
    `agregar_patrimonios`.
    NAO use para contratos ou licitacoes de aquisicao; para isso use
    `consultar_contratos` ou `consultar_licitacoes`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos:
            `unidade_responsavel`, `placa`, `descricao`, `classificacao`,
            `localizacao`, `status`, `situacao`, `tipo_ingresso`,
            `data_aquisicao_inicio` e `data_aquisicao_fim`. Datas em
            `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `data_aquisicao`,
            `valor_atualizado`, `valor_ingresso`, `descricao`, `localizacao`
            ou `placa`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos de
            patrimonio retornados em cada item.

    Returns:
        dict com:
        - `total`: total de bens encontrados antes da paginacao.
        - `resultados`: lista de bens; cada item pode incluir
          `unidade_responsavel`, `placa`, `descricao`, `classificacao`,
          `localizacao`, `status`, `situacao`, `tipo_ingresso`,
          `data_aquisicao`, `data_baixa`, `valor_ingresso` e
          `valor_atualizado`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum bem for encontrado.
    """
    try:
        params = ConsultarPatrimoniosParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarPatrimoniosMetadata(
            ordenar_por="data_aquisicao",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarPatrimoniosResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_patrimonios(session, params.filtros)
        total = len(registros)
        ordenados = sort_patrimonios(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = project_patrimonios(pagina, params.campos)

    metadata = ConsultarPatrimoniosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_PATRIMONIO_FIELDS),
    )

    if not resultados:
        return ConsultarPatrimoniosResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum bem patrimonial encontrado com os filtros.",
        ).model_dump(mode="json")

    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} bens encontrados."

    return ConsultarPatrimoniosResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
