"""Tool publica para consultas amplas do dominio de contratos."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, literal, select

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import (
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
)

from .consultar_contratos_schema import (
    ConsultarContratosMetadata,
    ConsultarContratosParams,
    ConsultarContratosResponse,
)
from .shared.filters import ALLOWED_CONTRACT_FIELDS, ContratosFiltroSchema
from .shared.querying import (
    apply_contratos_filters,
    build_contrato_details_unavailable_message,
    build_contract_fallback_message,
    build_descricao_despesa_unavailable_message,
    contratos_supports_detalhes_completos,
    contratos_supports_descricao_despesa,
    contratos_supports_xml_original,
    get_contratos_available_columns,
    project_contrato_fields,
)
from .shared.runtime import serializar_contrato_despesa, serializar_contrato_item


CONTRACT_ORDER_COLUMNS = {
    "numero": Contrato.numero,
    "fornecedor": Contrato.fornecedor,
    "valor": Contrato.valor,
    "data_inicio": Contrato.data_inicio,
    "data_fim": Contrato.data_fim,
    "categoria": Contrato.categoria,
    "secretaria": Contrato.secretaria,
}


def _fetch_contratos(
    session,
    params: ConsultarContratosParams,
    filtros: ContratosFiltroSchema,
    *,
    include_descricao_despesa: bool,
    include_xml_original: bool,
    available_columns: set[str],
) -> tuple[int, list[dict[str, Any]]]:
    """Executa a consulta principal de contratos com os filtros informados."""

    def _column_or_none(column_name: str, alias: str | None = None):
        target_alias = alias or column_name
        if column_name in available_columns:
            return getattr(Contrato, column_name).label(target_alias)
        return literal(None).label(target_alias)

    descricao_despesa_column = (
        Contrato.descricao_despesa.label("classificacao_da_despesa")
        if include_descricao_despesa
        else literal(None).label("classificacao_da_despesa")
    )
    extra_columns = []
    if params.incluir_detalhes:
        extra_columns = [
            _column_or_none("numero_licitatorio"),
            _column_or_none("numero_instrumento"),
            _column_or_none(
                "tipo_instrumento_contratual",
                alias="tipo_do_instrumento",
            ),
            _column_or_none("possui_aditivo"),
        ]
    base_stmt = apply_contratos_filters(
        select(
            Contrato.id.label("id"),
            Contrato.numero.label("numero"),
            Contrato.fornecedor.label("fornecedor"),
            Contrato.cnpj.label("documento_fornecedor"),
            Contrato.valor.label("valor"),
            Contrato.data_inicio.label("data_inicio"),
            Contrato.data_fim.label("data_fim"),
            Contrato.categoria.label("categoria"),
            Contrato.secretaria.label("secretaria"),
            Contrato.descricao.label("descricao"),
            descricao_despesa_column,
            *extra_columns,
        ),
        filtros,
        include_descricao_despesa=include_descricao_despesa,
        include_xml_original=include_xml_original,
        available_columns=available_columns,
    )
    total = session.execute(
        select(func.count()).select_from(base_stmt.order_by(None).subquery())
    ).scalar_one()

    order_column = CONTRACT_ORDER_COLUMNS[params.ordenar_por]
    ordered_stmt = base_stmt.order_by(
        order_column.desc() if params.ordem == "desc" else order_column.asc(),
        Contrato.id.desc(),
    )
    contratos = [
        dict(row)
        for row in session.execute(
            ordered_stmt.offset(params.offset).limit(params.limite)
        ).mappings()
    ]
    return total, contratos


def _attach_contract_details(
    session,
    contratos: list[dict[str, Any]],
    *,
    details_available: bool,
) -> list[dict[str, Any]]:
    """Acopla despesas e itens adquiridos ao payload quando solicitado."""

    if not contratos:
        return contratos

    if not details_available:
        for contrato in contratos:
            contrato.update(
                {
                    "total_despesas_orcamentarias": 0,
                    "despesas_orcamentarias": [],
                    "total_itens_adquiridos": 0,
                    "itens_adquiridos": [],
                }
            )
        return contratos

    contrato_ids = [contrato["id"] for contrato in contratos]
    despesas_rows = (
        session.execute(
            select(ContratoDespesaOrcamentaria)
            .where(ContratoDespesaOrcamentaria.contrato_id.in_(contrato_ids))
            .order_by(
                ContratoDespesaOrcamentaria.contrato_id.asc(),
                ContratoDespesaOrcamentaria.ordem.asc(),
            )
        )
        .scalars()
        .all()
    )
    itens_rows = (
        session.execute(
            select(ContratoItemAdquirido)
            .where(ContratoItemAdquirido.contrato_id.in_(contrato_ids))
            .order_by(
                ContratoItemAdquirido.contrato_id.asc(),
                ContratoItemAdquirido.ordem.asc(),
            )
        )
        .scalars()
        .all()
    )

    despesas_por_contrato: dict[int, list[dict[str, Any]]] = {}
    for despesa in despesas_rows:
        despesas_por_contrato.setdefault(despesa.contrato_id, []).append(
            serializar_contrato_despesa(despesa)
        )

    itens_por_contrato: dict[int, list[dict[str, Any]]] = {}
    for item in itens_rows:
        itens_por_contrato.setdefault(item.contrato_id, []).append(
            serializar_contrato_item(item)
        )

    for contrato in contratos:
        despesas = despesas_por_contrato.get(contrato["id"], [])
        itens = itens_por_contrato.get(contrato["id"], [])
        contrato.update(
            {
                "total_despesas_orcamentarias": len(despesas),
                "despesas_orcamentarias": despesas,
                "total_itens_adquiridos": len(itens),
                "itens_adquiridos": itens,
            }
        )
    return contratos


def _execute_fallback_candidates(
    session,
    params: ConsultarContratosParams,
    *,
    include_descricao_despesa: bool,
    include_xml_original: bool,
    available_columns: set[str],
) -> tuple[ContratosFiltroSchema, int, list[dict[str, Any]], str, str] | None:
    """
    Tenta filtros alternativos em colunas semanticamente proximas.

    O primeiro fallback com resultado e usado. Isso deixa o comportamento
    previsivel e evita mesclar registros de varias estrategias diferentes.
    """

    source_field = next(
        (
            field_name
            for field_name in ("fornecedor", "descricao", "categoria", "secretaria")
            if getattr(params.filtros, field_name) is not None
        ),
        "",
    )
    for (
        target_field,
        fallback_filters,
    ) in params.filtros.build_text_fallback_candidates():
        fallback_total, fallback_contratos = _fetch_contratos(
            session,
            params,
            fallback_filters,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
            available_columns=available_columns,
        )
        if fallback_total > 0:
            return (
                fallback_filters,
                fallback_total,
                fallback_contratos,
                source_field,
                target_field,
            )
    return None


@register(
    name="consultar_contratos",
    scope=PUBLIC_SCOPE,
    tags=["domain:contratos", "shape:lookup"],
)
def consultar_contratos(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_inicio",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
    incluir_detalhes: bool = False,
) -> dict[str, Any]:
    """
    Lista contratos por numero, fornecedor, secretaria, categoria, descricao e valor.

    Use esta tool quando a pergunta pedir quais contratos existem, detalhes de um
    contrato especifico ou uma listagem filtrada.
    NAO use para totais, medias ou rankings agregados; para isso use
    `agregar_contratos`.
    NAO use para perguntas sobre o processo licitatorio antes da assinatura do
    contrato, como modalidade, situacao da licitacao ou edital; para isso use
    `consultar_licitacoes`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `numero`,
            `fornecedor`, `documento_fornecedor`, `categoria`, `secretaria`,
            `descricao`, `data_inicio`, `data_inicio_inicio`, `data_inicio_fim`,
            `valor_min` e `valor_max`. Datas em `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `numero`, `fornecedor`, `valor`,
            `data_inicio`, `data_fim`, `categoria` ou `secretaria`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional de campos por item. Cada item pode incluir `id`,
            `numero`, `fornecedor`, `documento_fornecedor`, `valor`,
            `data_inicio`, `data_fim`, `categoria`, `secretaria`, `descricao`
            e `classificacao_da_despesa`.
        incluir_detalhes: Se `True`, inclui detalhes adicionais do contrato,
            despesas orcamentarias e itens adquiridos quando esses dados existirem.

    Returns:
        dict com:
        - `total`: total de contratos encontrados antes da paginacao.
        - `resultados`: lista de contratos com os campos solicitados; quando
          `incluir_detalhes=True`, cada item pode trazer tambem
          `numero_licitatorio`, `numero_instrumento`, `tipo_do_instrumento`,
          `possui_aditivo`, `despesas_orcamentarias` e `itens_adquiridos`.
        - `metadata`: filtros aplicados, possiveis filtros de fallback,
          ordenacao, paginacao e se houve pedido de detalhes.
        - `mensagem`: aviso quando a resposta estiver paginada ou quando houver
          alguma observacao relevante.
        - `sugestao`: dica quando nenhum contrato for encontrado.
    """
    try:
        params = ConsultarContratosParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
                "incluir_detalhes": incluir_detalhes,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarContratosMetadata(
            ordenar_por="data_inicio",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarContratosResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        available_columns = get_contratos_available_columns(session)
        include_descricao_despesa = contratos_supports_descricao_despesa(session)
        include_xml_original = contratos_supports_xml_original(session)
        details_available = contratos_supports_detalhes_completos(session)
        filtros_execucao = params.filtros
        total, contratos = _fetch_contratos(
            session,
            params,
            filtros_execucao,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
            available_columns=available_columns,
        )
        fallback_aplicado = False
        fallback_source_field = ""
        fallback_target_field = ""

        if total == 0:
            fallback_result = _execute_fallback_candidates(
                session,
                params,
                include_descricao_despesa=include_descricao_despesa,
                include_xml_original=include_xml_original,
                available_columns=available_columns,
            )
            if fallback_result is not None:
                (
                    filtros_execucao,
                    total,
                    contratos,
                    fallback_source_field,
                    fallback_target_field,
                ) = fallback_result
                fallback_aplicado = True

        if params.incluir_detalhes:
            contratos = _attach_contract_details(
                session,
                contratos,
                details_available=details_available,
            )

    metadata = ConsultarContratosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        filtros_fallback_aplicados=(
            filtros_execucao.to_metadata_dict() if fallback_aplicado else None
        ),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        incluir_detalhes=params.incluir_detalhes,
        campos=params.campos or list(ALLOWED_CONTRACT_FIELDS),
    )

    if not contratos:
        sugestao = "Nenhum contrato encontrado com os filtros informados."
        if not include_descricao_despesa:
            sugestao = (
                build_descricao_despesa_unavailable_message(params.filtros) or sugestao
            )
        if params.incluir_detalhes and not details_available:
            sugestao = build_contrato_details_unavailable_message()
        return ConsultarContratosResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao=sugestao,
        ).model_dump(mode="json")

    resultados = [
        project_contrato_fields(contrato, params.campos) for contrato in contratos
    ]
    mensagens: list[str] = []
    if not include_descricao_despesa:
        warning = build_descricao_despesa_unavailable_message(params.filtros)
        if warning is not None:
            mensagens.append(warning)
    if params.incluir_detalhes and not details_available:
        mensagens.append(build_contrato_details_unavailable_message())
    if fallback_aplicado:
        mensagens.append(
            build_contract_fallback_message(
                fallback_source_field,
                fallback_target_field,
            )
        )
    if total > len(resultados):
        mensagens.append(
            f"Mostrando {len(resultados)} de {total} registros encontrados."
        )
    mensagem = " ".join(mensagens) or None

    return ConsultarContratosResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
