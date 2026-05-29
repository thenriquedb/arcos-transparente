"""Tool publica para consultas de politicos eleitos."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Eleito
from shared.utils.text import matches_text_query

from .consultar_eleitos_schema import (
    ALLOWED_ELEITO_FIELDS,
    ConsultarEleitosMetadata,
    ConsultarEleitosParams,
    ConsultarEleitosResponse,
    EleitoFiltroSchema,
)


def _row_to_public_dict(registro: Eleito) -> dict[str, Any]:
    return {
        "tipo_politico": registro.tipo_politico,
        "id_origem": registro.id_origem,
        "nome_completo": registro.nome_completo,
        "nome_popular": registro.nome_popular,
        "partido": registro.partido,
        "telefone": registro.telefone,
        "email": registro.email,
        "homepage": registro.homepage,
        "numero_gabinete": registro.numero_gabinete,
        "cargo": registro.cargo,
        "biografia": registro.biografia,
        "mandato_inicio": registro.mandato_inicio,
        "mandato_fim": registro.mandato_fim,
        "mandato_status": registro.mandato_status,
        "mandato_observacao": registro.mandato_observacao,
        "municipio": registro.municipio,
        "estado": registro.estado,
    }


def _load_filtered_eleitos(session, filtros: EleitoFiltroSchema) -> list[Eleito]:
    registros = session.query(Eleito).all()

    if filtros.tipo_politico:
        registros = [
            r
            for r in registros
            if matches_text_query(r.tipo_politico, filtros.tipo_politico)
        ]
    if filtros.nome:
        registros = [
            r for r in registros if matches_text_query(r.nome_completo, filtros.nome)
        ]
    if filtros.nome_popular:
        registros = [
            r
            for r in registros
            if matches_text_query(r.nome_popular, filtros.nome_popular)
        ]
    if filtros.partido:
        registros = [
            r for r in registros if matches_text_query(r.partido, filtros.partido)
        ]
    if filtros.cargo:
        registros = [r for r in registros if matches_text_query(r.cargo, filtros.cargo)]
    if filtros.status_mandato:
        registros = [
            r
            for r in registros
            if matches_text_query(r.mandato_status, filtros.status_mandato)
        ]
    if filtros.ano:
        registros = [
            r for r in registros if r.mandato_inicio <= filtros.ano <= r.mandato_fim
        ]
    if filtros.em_exercicio is True:
        registros = [
            r for r in registros if matches_text_query(r.mandato_status, "em exercicio")
        ]
    if filtros.em_exercicio is False:
        registros = [
            r
            for r in registros
            if not matches_text_query(r.mandato_status, "em exercicio")
        ]
    if filtros.municipio:
        registros = [
            r for r in registros if matches_text_query(r.municipio, filtros.municipio)
        ]
    if filtros.estado:
        registros = [
            r for r in registros if matches_text_query(r.estado, filtros.estado)
        ]

    return registros


def _sort_eleitos(
    registros: list[Eleito],
    ordenar_por: str,
    ordem: str,
) -> list[Eleito]:
    reverse = ordem == "desc"

    def key(registro: Eleito) -> Any:
        mapping = {
            "mandato_inicio": registro.mandato_inicio,
            "mandato_fim": registro.mandato_fim,
            "nome": registro.nome_completo or "",
            "partido": registro.partido or "",
            "tipo_politico": registro.tipo_politico or "",
        }
        return mapping[ordenar_por]

    return sorted(registros, key=key, reverse=reverse)


def _project_eleitos(
    registros: list[Eleito],
    campos: list[str],
) -> list[dict[str, Any]]:
    selected = campos or list(ALLOWED_ELEITO_FIELDS)
    return [
        {
            campo: value
            for campo, value in _row_to_public_dict(registro).items()
            if campo in selected
        }
        for registro in registros
    ]


@register(
    name="consultar_eleitos",
    scope=PUBLIC_SCOPE,
    tags=["domain:eleitos", "shape:lookup"],
)
def consultar_eleitos(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "mandato_inicio",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista vereadores,prefeitos e vice-prefeitos eleitos, com partido e periodo de mandato.

    Use esta tool quando a pergunta pedir quem foram/quem são os eleitos,
    quais mandatos uma pessoa teve, partido de um eleito ou status do mandato.
    Para cargo politico atual, use `em_exercicio=True` e o `tipo_politico`
    correspondente, por exemplo `tipo_politico="prefeito"`.
    NAO use esta tool para perguntas sobre politicos que NAO sejam sobre mandatos de vereadores, prefeitos ou vice-prefeitos,
    NAO use como fonte final para responder valores de despesas, salarios,
    receitas, licitacoes, contratos, servidores ou folha. Para esses temas,
    use as tools especificas de cada dominio.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos:
            `tipo_politico` (`vereador`, `prefeito` ou `vice-prefeito`), `nome`, `nome_popular`,
            `partido`, `cargo`, `status_mandato`, `ano`, `em_exercicio`,
            `municipio` e `estado`.
        ordenar_por: Campo de ordenacao. Aceita `mandato_inicio`, `mandato_fim`,
            `nome`, `partido` ou `tipo_politico`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos
            retornados por item.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de eleitos com os campos solicitados.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum registro for encontrado.
    """
    try:
        params = ConsultarEleitosParams.model_validate(
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
        fallback_metadata = ConsultarEleitosMetadata(
            ordenar_por="mandato_inicio",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarEleitosResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = _load_filtered_eleitos(session, params.filtros)
        total = len(registros)
        ordenados = _sort_eleitos(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = _project_eleitos(pagina, params.campos)

    metadata = ConsultarEleitosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_ELEITO_FIELDS),
    )

    if not resultados:
        return ConsultarEleitosResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum politico eleito encontrado com os filtros.",
        ).model_dump(mode="json")

    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarEleitosResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
