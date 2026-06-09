"""Modulo de ingestao adapter and loader for receitas."""

from __future__ import annotations

from typing import Any

from database.models import ReceitaArrecadacao, ReceitaLancamento
from ingestion.loaders.sql_loader import LoadResult, SQLLoader
from ingestion.parsers.xml.shared import sanitize_xml_payload

from .adapters import build_pipeline_bulk_adapter
from .discovery import discover_receitas_files
from .shared import apply_upsert_status, merge_load_results, upsert_by_filters


def load_receitas(
    session,
    *,
    arquivos: list,
    parser,
    batch_size: int,
    ano: int | None,
    get_or_create_natureza,
    to_date,
) -> LoadResult:
    """Load receita arrecadacoes and lancamentos across the discovered file set."""

    resultado = LoadResult()
    arquivos_arrec = [
        arquivo for arquivo in arquivos if "arrecadacao" in arquivo.name.lower()
    ]
    arquivos_lanc = [
        arquivo for arquivo in arquivos if "lancamento" in arquivo.name.lower()
    ]

    for arquivo in arquivos_arrec:
        for registro in parser.parse_arrecadacoes(str(arquivo)):
            registro = sanitize_xml_payload(registro)
            try:
                with session.begin():
                    natureza = get_or_create_natureza(
                        session,
                        registro.get("natureza") or {},
                    )
                    payload = {
                        "exercicio": registro["exercicio"],
                        "mes": registro["mes"],
                        "data_arrecadacao": to_date(registro["data_arrecadacao"]),
                        "unidade_gestora": registro["unidade_gestora"],
                        "natureza_id": natureza.id if natureza else None,
                        "fonte_recurso": registro.get("fonte_recurso"),
                        "valor_previsto_bruto": registro.get("valor_previsto_bruto"),
                        "valor_arrecadado_bruto": registro.get(
                            "valor_arrecadado_bruto"
                        ),
                        "valor_previsto_deducoes": registro.get(
                            "valor_previsto_deducoes"
                        ),
                        "valor_realizado_deducoes": registro.get(
                            "valor_realizado_deducoes"
                        ),
                        "valor_previsto_liquido": registro.get(
                            "valor_previsto_liquido"
                        ),
                        "valor_arrecadado_liquido": registro.get(
                            "valor_arrecadado_liquido"
                        ),
                    }
                    _, status = upsert_by_filters(
                        session,
                        ReceitaArrecadacao,
                        filters=[
                            ReceitaArrecadacao.data_arrecadacao
                            == payload["data_arrecadacao"],
                            ReceitaArrecadacao.unidade_gestora
                            == payload["unidade_gestora"],
                            ReceitaArrecadacao.natureza_id == payload["natureza_id"],
                            ReceitaArrecadacao.fonte_recurso
                            == payload["fonte_recurso"],
                        ],
                        payload=payload,
                    )
                    apply_upsert_status(resultado, status)
            except Exception:
                session.rollback()
                resultado.erros += 1

    loader = SQLLoader(session=session, batch_size=batch_size)
    for arquivo in arquivos_lanc:
        parcial = loader.load(
            parser.parse_lancamentos(str(arquivo)),
            ReceitaLancamento,
        )
        merge_load_results(resultado, parcial)

    return resultado


ADAPTER = build_pipeline_bulk_adapter(
    "receitas",
    discover_files=discover_receitas_files,
    pipeline_method_name="_load_receitas",
)
