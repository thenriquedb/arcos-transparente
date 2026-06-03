"""Tool publica para consultas amplas do dominio de servidores."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from database import session as session_manager
from database.models import Servidor

from .consultar_servidores_schema import (
    ConsultarServidoresMetadata,
    ConsultarServidoresParams,
    ConsultarServidoresResponse,
)
from .shared.filters import ALLOWED_SERVER_FIELDS
from .shared.querying import (
    apply_servidores_filters,
    project_servidor_fields,
    resolve_mes_de_referencia_padrao,
)


SERVER_ORDER_COLUMNS = {
    "nome": Servidor.nome,
    "cargo": Servidor.cargo,
    "secretaria": Servidor.secretaria,
    "salario_base": Servidor.salario_base,
    "mes_de_referencia": Servidor.competencia_referencia,
}


@register(
    name="consultar_servidores",
    scope=PUBLIC_SCOPE,
    tags=["domain:servidores", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quais servidores da educacao?",
            "Quais os 10 maiores salarios da prefeitura?",
        ],
        hints=[
            "servidor",
            "cargo",
            "secretaria",
            "lista",
            "maiores salarios",
        ],
    ),
)
def consultar_servidores(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "nome",
    ordem: str = "asc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista registros cadastrais de servidores por nome, cargo e secretaria.

    Use esta tool quando a pergunta pedir quem sao os servidores, quais nomes aparecem
    ou um ranking simples por ordenacao, como maiores salarios da prefeitura.
    NAO use para responder salario individual, valor recebido, "quanto recebe",
    "qual o salario de [pessoa]", "qual o salario dele" ou salario de prefeito,
    vice ou vereador. Para esses casos, use
    `buscar_historico_de_pagamentos_do_servidor`; se o usuário disser apenas
    "prefeito", "vice" ou "vereador", use antes `consultar_eleitos` para obter
    o nome completo.
    NAO use para totais, contagens ou agrupamentos; para isso use
    `agregar_servidores`.
    NAO use para historico mensal de pagamento de um servidor com nome informado;
    para isso use `buscar_historico_de_pagamentos_do_servidor`.

    Se `mes_de_referencia` nao for informado, a consulta usa o mes mais recente com
    dados para evitar misturar snapshots de meses diferentes.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `nome`, `secretaria`,
            `cargo`, `mes_de_referencia`, `mes_de_referencia_inicio`,
            `mes_de_referencia_fim`, `salario_min` e `salario_max`.
            Datas em `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `nome`, `cargo`, `secretaria`,
            `salario_base` ou `mes_de_referencia`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional de campos por item. Cada item pode incluir `id`,
            `nome`, `cargo`, `secretaria`, `salario_base` e
            `mes_de_referencia`.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de servidores com os campos solicitados.
        - `metadata`: filtros aplicados, ordenacao, paginacao e o
          `mes_de_referencia_considerado`.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum registro for encontrado.
    """
    try:
        params = ConsultarServidoresParams.model_validate(
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
        fallback_metadata = ConsultarServidoresMetadata(
            ordenar_por="nome",
            ordem="asc",
            limite=10,
            offset=0,
        )
        return ConsultarServidoresResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        mes_de_referencia_considerado, mes_padrao_aplicado = (
            resolve_mes_de_referencia_padrao(
                session,
                params.filtros,
            )
        )

        base_stmt = apply_servidores_filters(
            select(Servidor),
            params.filtros,
            mes_de_referencia_considerado=mes_de_referencia_considerado,
        )
        total = session.execute(
            select(func.count()).select_from(base_stmt.order_by(None).subquery())
        ).scalar_one()

        order_column = SERVER_ORDER_COLUMNS[params.ordenar_por]
        ordered_stmt = base_stmt.order_by(
            order_column.desc() if params.ordem == "desc" else order_column.asc(),
            Servidor.nome.asc(),
        )
        servidores = (
            session.execute(ordered_stmt.offset(params.offset).limit(params.limite))
            .scalars()
            .all()
        )

    metadata = ConsultarServidoresMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_SERVER_FIELDS),
        mes_de_referencia_considerado=mes_de_referencia_considerado,
        mes_de_referencia_padrao_aplicado=mes_padrao_aplicado,
    )

    if not servidores:
        return ConsultarServidoresResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum servidor encontrado com os filtros informados.",
        ).model_dump(mode="json")

    resultados = [
        project_servidor_fields(servidor, params.campos) for servidor in servidores
    ]
    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarServidoresResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
