"""Tool publica para consultar veiculos de frota."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import FrotaVeiculo
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_frota_schema import (
    ALLOWED_FROTA_FIELDS,
    ConsultarFrotaMetadata,
    ConsultarFrotaParams,
    ConsultarFrotaResponse,
    FrotaFiltroSchema,
)


def _total_despesas(registro: FrotaVeiculo) -> Decimal:
    return sum(despesa.total_despesa or Decimal("0") for despesa in registro.despesas)


def _row_to_public_dict(registro: FrotaVeiculo) -> dict[str, Any]:
    return {
        "codigo_veiculo": registro.codigo_veiculo,
        "placa_patrimonio": registro.placa_patrimonio,
        "placa_veiculo": registro.placa_veiculo,
        "descricao_material": registro.descricao_material,
        "unidade_responsavel": registro.unidade_gestora,
        "tipo_veiculo": registro.tipo_veiculo,
        "marca": registro.marca,
        "modelo": registro.modelo,
        "data_aquisicao": registro.data_aquisicao.date().isoformat()
        if registro.data_aquisicao
        else None,
        "localizacao": registro.localizacao,
        "descricao": registro.descricao,
        "ano_fabricacao": registro.ano_fabricacao,
        "situacao_veiculo": registro.situacao_veiculo,
        "situacao_patrimonial": registro.situacao_veiculo_patrimonio,
        "estado_conservacao": registro.estado_conservacao,
        "ano_modelo": registro.ano_modelo,
        "qtd_passageiros": registro.qtd_passageiros,
        "valor_atual": decimal_to_float(registro.valor_atual),
        "total_despesas": decimal_to_float(_total_despesas(registro)),
    }


def load_filtered_frota(
    session,
    filtros: FrotaFiltroSchema,
) -> list[FrotaVeiculo]:
    registros = session.query(FrotaVeiculo).all()

    if filtros.unidade_responsavel:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_responsavel)
        ]
    if filtros.placa:
        registros = [
            r
            for r in registros
            if matches_text_query(r.placa_veiculo, filtros.placa)
            or matches_text_query(r.placa_patrimonio, filtros.placa)
        ]
    if filtros.descricao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.descricao_material, filtros.descricao)
            or matches_text_query(r.descricao, filtros.descricao)
        ]
    if filtros.tipo_veiculo:
        registros = [
            r
            for r in registros
            if matches_text_query(r.tipo_veiculo, filtros.tipo_veiculo)
        ]
    if filtros.marca:
        registros = [r for r in registros if matches_text_query(r.marca, filtros.marca)]
    if filtros.modelo:
        registros = [
            r for r in registros if matches_text_query(r.modelo, filtros.modelo)
        ]
    if filtros.situacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.situacao_veiculo, filtros.situacao)
            or matches_text_query(r.situacao_veiculo_patrimonio, filtros.situacao)
        ]
    if filtros.localizacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.localizacao, filtros.localizacao)
        ]
    if filtros.data_aquisicao_inicio:
        registros = [
            r
            for r in registros
            if r.data_aquisicao is not None
            and r.data_aquisicao.date() >= filtros.data_aquisicao_inicio
        ]
    if filtros.data_aquisicao_fim:
        registros = [
            r
            for r in registros
            if r.data_aquisicao is not None
            and r.data_aquisicao.date() <= filtros.data_aquisicao_fim
        ]

    return registros


def sort_frota(
    registros: list[FrotaVeiculo],
    ordenar_por: str,
    ordem: str,
) -> list[FrotaVeiculo]:
    reverse = ordem == "desc"

    def key(registro: FrotaVeiculo) -> Any:
        mapping = {
            "data_aquisicao": registro.data_aquisicao,
            "codigo_veiculo": registro.codigo_veiculo or "",
            "placa_veiculo": registro.placa_veiculo or "",
            "tipo_veiculo": registro.tipo_veiculo or "",
            "modelo": registro.modelo or "",
            "valor_atual": registro.valor_atual or Decimal("0"),
            "total_despesas": _total_despesas(registro),
        }
        return mapping[ordenar_por] or ""

    return sorted(registros, key=key, reverse=reverse)


def project_frota(
    registros: list[FrotaVeiculo],
    campos: list[str],
) -> list[dict[str, Any]]:
    selected = campos or list(ALLOWED_FROTA_FIELDS)
    return [
        {
            campo: value
            for campo, value in _row_to_public_dict(registro).items()
            if campo in selected
        }
        for registro in registros
    ]


@register(
    name="consultar_frota",
    scope=PUBLIC_SCOPE,
    tags=["domain:frotas", "shape:lookup"],
)
def consultar_frota(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "codigo_veiculo",
    ordem: str = "asc",
    limite: int = 20,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista veiculos da frota por unidade, placa, tipo, marca, modelo e situacao.

    Use esta tool quando a pergunta mencionar veiculos, carros, caminhoes,
    maquinas, ambulancias, onibus, placas, frota da prefeitura ou frota da
    camara. Ela responde quais veiculos existem e seus dados cadastrais.
    NAO use para horarios de onibus, linhas intermunicipais, contatos
    institucionais, estrutura organizacional ou outras perguntas documentais do
    acervo markdown local; para isso use `consultar_conhecimento_municipal`.
    NAO use para bens patrimoniais em geral; para isso use
    `consultar_patrimonios`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos:
            `unidade_responsavel`, `placa`, `descricao`, `tipo_veiculo`,
            `marca`, `modelo`, `situacao`, `localizacao`,
            `data_aquisicao_inicio` e `data_aquisicao_fim`.
        ordenar_por: Campo de ordenacao. Aceita `data_aquisicao`,
            `codigo_veiculo`, `placa_veiculo`, `tipo_veiculo`, `modelo`,
            `valor_atual` ou `total_despesas`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos
            retornados em cada veiculo.

    Returns:
        dict com:
        - `total`: total de veiculos encontrados antes da paginacao.
        - `resultados`: lista de veiculos.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum veiculo for encontrado.
    """
    try:
        params = ConsultarFrotaParams.model_validate(
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
        fallback_metadata = ConsultarFrotaMetadata(
            ordenar_por="codigo_veiculo",
            ordem="asc",
            limite=20,
            offset=0,
        )
        return ConsultarFrotaResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_frota(session, params.filtros)
        total = len(registros)
        ordenados = sort_frota(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = project_frota(pagina, params.campos)

    metadata = ConsultarFrotaMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_FROTA_FIELDS),
    )

    if not resultados:
        return ConsultarFrotaResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum veiculo de frota encontrado com os filtros.",
        ).model_dump(mode="json")

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = (
            f"Exibindo {len(resultados)} de {total} veiculos encontrados. "
            "Use limite e offset para navegar."
        )

    return ConsultarFrotaResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
