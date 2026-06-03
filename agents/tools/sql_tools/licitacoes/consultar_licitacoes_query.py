"""Tool publica para consultas amplas do dominio de licitacoes."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from database import session as session_manager
from database.models import InstrumentoContratual, Licitacao
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_licitacoes_schema import (
    ConsultarLicitacoesMetadata,
    ConsultarLicitacoesParams,
    ConsultarLicitacoesResponse,
)
from .shared.filters import ALLOWED_BIDDING_FIELDS
from .shared.querying import (
    apply_licitacoes_filters,
    project_licitacao_fields,
)


BIDDING_ORDER_COLUMNS = {
    "numero": Licitacao.numero,
    "modalidade": Licitacao.modalidade,
    "valor_estimado": Licitacao.valor_estimado,
    "data_abertura": Licitacao.data_abertura,
    "situacao": Licitacao.situacao,
    "secretaria": Licitacao.secretaria,
}

_SUGESTAO_SEM_RESULTADOS = (
    "Nenhuma licitacao encontrada com os filtros informados. "
    "Consulte tambem `consultar_contratos` com os mesmos termos — "
    "o servico ou evento pode ja ter sido contratado diretamente "
    "sem processo licitatorio registrado na base."
)

_AVISO_VALOR_ESTIMADO_ZERO = (
    "Valor estimado registrado como R$ 0,00. Esse campo pode nao ter "
    "sido preenchido no portal de origem. Consulte `consultar_contratos` "
    "com o mesmo objeto ou fornecedor para verificar o valor contratado."
)


def _valor_estimado_e_zero(valor: Any) -> bool:
    """Retorna True quando o valor estimado esta ausente ou igual a zero."""
    if valor is None:
        return True
    try:
        return float(valor) == 0.0
    except (TypeError, ValueError):
        return False


def _somar_valor_estimado(licitacoes: list) -> float:
    """
    Soma os valores estimados de uma lista de licitacoes.
    Ignora registros com valor None para evitar TypeError no sum().
    """
    return float(
        sum(l.valor_estimado for l in licitacoes if l.valor_estimado is not None)
    )


def _aplicar_aviso_valor_estimado_zero(
    resultados: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Adiciona campo 'aviso' em licitacoes com valor estimado zero ou ausente.

    Orienta o LLM a consultar contratos para verificar o valor real contratado.
    """
    for licitacao in resultados:
        if "valor_estimado" in licitacao and _valor_estimado_e_zero(
            licitacao.get("valor_estimado")
        ):
            licitacao["aviso"] = _AVISO_VALOR_ESTIMADO_ZERO
    return resultados


@register(
    name="consultar_licitacoes",
    scope=PUBLIC_SCOPE,
    tags=["domain:licitacoes", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quais licitacoes estao abertas?",
            "Houve licitacao para o Natal Fest?",
        ],
        hints=[
            "licitacao",
            "edital",
            "objeto",
            "modalidade",
            "fornecedor vencedor",
        ],
    ),
)
def consultar_licitacoes(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_abertura",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
    incluir_detalhes: bool = False,
    max_vencedores: int = 5,
    max_instrumentos: int = 5,
    max_itens: int = 10,
) -> dict[str, Any]:
    """
    Lista licitacoes por numero, modalidade, objeto, situacao, secretaria e valor.

    Use para perguntas sobre processos licitatorios, editais, fornecedores
    vencedores ou detalhes de uma licitacao especifica.
    Exemplos:
    - 'quais licitacoes estao abertas?'
    - 'licitacoes da secretaria de saude em 2024'
    - 'a empresa X ganhou alguma licitacao?'
    - 'qual o valor estimado das licitacoes de obras?'
    - 'houve licitacao para o Natal Fest?' (busca por objeto do evento)
    - 'licitacoes por dispensa em 2024'

    Quando esta tool retornar resultado vazio, consulte tambem
    `consultar_contratos` com os mesmos termos antes de concluir que nao
    ha dados — o servico pode ter sido contratado diretamente sem processo
    licitatorio registrado na base.

    Quando esta tool retornar licitacao com valor estimado R$ 0,00, o campo
    'aviso' do resultado ja orienta a proxima acao. Nesse caso, consulte
    `consultar_contratos` com o mesmo objeto ou fornecedor para verificar
    o valor efetivamente contratado.

    Quando a pergunta for sobre "gasto" ou "custo" de um evento, servico,
    fornecedor ou outro objeto contratual, apresente as licitacoes como lista
    detalhada de valores estimados e deixe claro que licitacao nao e a mesma
    coisa que contrato nem pagamento efetivo. Nesses casos, cruze a resposta
    com `consultar_contratos` e `consultar_despesas` quando essas fontes
    tambem forem relevantes.

    O retorno inclui `valor_total_estimado`, que soma todas as licitacoes
    encontradas pelos filtros, mesmo quando a lista exibida estiver paginada.
    Trate esse valor como estimado — nao representa gasto efetivo realizado.

    Se o filtro textual vier apenas de uma sigla curta ou termo ambiguo,
    como 'UPA', 'UBS', 'PSF', 'CRAS' ou 'CREAS', primeiro confirme o
    significado com o usuario e sugira a expansao provavel. So use a tool
    depois dessa confirmacao.

    NAO use para contratos ja assinados ou executados; para isso use
    `consultar_contratos`.
    NAO use para totais, medias ou rankings agregados; para isso use
    `agregar_licitacoes`.
    NAO use para pagamentos efetivos realizados; para isso use
    `consultar_despesas`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `numero`,
            `modalidade`, `objeto`, `secretaria`, `situacao`, `fornecedor`,
            `cnpj_cpf`, `data_abertura`, `data_abertura_inicio`,
            `data_abertura_fim`, `valor_estimado_min` e `valor_estimado_max`.
            Datas em `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `numero`, `modalidade`,
            `valor_estimado`, `data_abertura`, `situacao` ou `secretaria`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional de campos por item. Cada item pode incluir `id`,
            `numero`, `modalidade`, `objeto`, `valor_estimado`, `data_abertura`,
            `situacao` e `secretaria`.
        incluir_detalhes: Se `True`, inclui vencedores, instrumentos contratuais
            e itens relacionados quando esses dados existirem.
        max_vencedores: Maximo de vencedores por licitacao. Inteiro de 1 a 20.
        max_instrumentos: Maximo de instrumentos contratuais por licitacao.
            Inteiro de 1 a 20.
        max_itens: Maximo de itens retornados por instrumento. Inteiro de 1 a 50.

    Returns:
        dict com:
        - `total`: total de licitacoes encontradas antes da paginacao.
        - `valor_total_estimado`: soma do valor estimado de todas as licitacoes
          que combinaram com os filtros. Trate como estimado, nao como gasto
          efetivo realizado.
        - `resultados`: lista de licitacoes com os campos solicitados; quando
          `incluir_detalhes=True`, cada item pode trazer vencedores,
          instrumentos contratuais e itens; quando o valor estimado for zero
          ou ausente, o campo `aviso` orienta a consulta em
          `consultar_contratos`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e se houve pedido
          de detalhes.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhuma licitacao for encontrada, incluindo
          orientacao para consultar `consultar_contratos` com os mesmos termos.
    """
    try:
        params = ConsultarLicitacoesParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
                "incluir_detalhes": incluir_detalhes,
                "max_vencedores": max_vencedores,
                "max_instrumentos": max_instrumentos,
                "max_itens": max_itens,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarLicitacoesMetadata(
            ordenar_por="data_abertura",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarLicitacoesResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        base_stmt = apply_licitacoes_filters(select(Licitacao), params.filtros)
        order_column = BIDDING_ORDER_COLUMNS[params.ordenar_por]
        ordered_stmt = base_stmt.order_by(
            order_column.desc() if params.ordem == "desc" else order_column.asc(),
            Licitacao.numero.asc(),
        )

        if params.incluir_detalhes:
            ordered_stmt = ordered_stmt.options(
                selectinload(Licitacao.vencedores),
                selectinload(Licitacao.instrumentos_contratuais).selectinload(
                    InstrumentoContratual.materias
                ),
                selectinload(Licitacao.instrumentos_contratuais).selectinload(
                    InstrumentoContratual.fornecedor
                ),
            )

        if params.filtros.objeto:
            todas_licitacoes_filtradas = [
                licitacao
                for licitacao in session.execute(ordered_stmt).scalars().all()
                if matches_text_query(licitacao.objeto, params.filtros.objeto)
            ]
            total = len(todas_licitacoes_filtradas)

            # Ignora None no sum para evitar TypeError
            valor_total_estimado = _somar_valor_estimado(todas_licitacoes_filtradas)

            licitacoes = todas_licitacoes_filtradas[
                params.offset : params.offset + params.limite
            ]
        else:
            total = session.execute(
                select(func.count()).select_from(base_stmt.order_by(None).subquery())
            ).scalar_one()
            total_subquery = base_stmt.order_by(None).subquery()
            valor_total_estimado = session.execute(
                select(func.coalesce(func.sum(total_subquery.c.valor_estimado), 0))
            ).scalar_one()
            licitacoes = (
                session.execute(ordered_stmt.offset(params.offset).limit(params.limite))
                .scalars()
                .all()
            )

        resultados = [
            project_licitacao_fields(
                licitacao,
                params.campos,
                incluir_detalhes=params.incluir_detalhes,
                max_vencedores=params.max_vencedores,
                max_instrumentos=params.max_instrumentos,
                max_itens=params.max_itens,
            )
            for licitacao in licitacoes
        ]

    metadata = ConsultarLicitacoesMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_BIDDING_FIELDS),
        incluir_detalhes=params.incluir_detalhes,
    )

    if not resultados:
        return ConsultarLicitacoesResponse(
            total=0,
            valor_total_estimado=0.0,
            resultados=[],
            metadata=metadata,
            sugestao=_SUGESTAO_SEM_RESULTADOS,
        ).model_dump(mode="json")

    # Sinaliza licitacoes com valor estimado zero para o LLM encadear com contratos
    resultados = _aplicar_aviso_valor_estimado_zero(resultados)

    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarLicitacoesResponse(
        total=total,
        valor_total_estimado=decimal_to_float(valor_total_estimado),
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
