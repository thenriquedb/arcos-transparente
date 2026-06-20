from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.tools.sql_tools.shared.empty_state import resolve_empty_result_suggestion
import agents.tools.sql_tools.shared.empty_state as empty_state_module
from database.models import Base, ReceitaArrecadacao


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return session_local()


def _write_source_file(tmp_path, relative_path: str) -> None:
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("placeholder", encoding="utf-8")


def test_resolve_empty_result_suggestion_detects_missing_import_from_shared_registry(
    monkeypatch,
    tmp_path,
) -> None:
    session = _build_session()
    _write_source_file(tmp_path, "despesas/despesas-por-funcao/despesas-por-funcao-prefeitura-2025.csv")
    monkeypatch.setattr(empty_state_module, "get_cli_data_directory", lambda: tmp_path)

    suggestion = resolve_empty_result_suggestion(
        session,
        domain_key="despesas_por_funcao",
        filters={"ano": 2025, "origem": "prefeitura"},
        default_suggestion="Nenhum registro de despesas por funcao encontrado com os filtros.",
    )

    assert suggestion == (
        "Os arquivos-fonte de despesas por funcao para 2025 e origem prefeitura existem no ambiente, "
        "mas esse dominio ainda nao foi importado no banco local. Reimporte a base SQLite antes de "
        "responder essa pergunta."
    )

    session.close()


def test_resolve_empty_result_suggestion_respects_dynamic_receita_type(
    monkeypatch,
    tmp_path,
) -> None:
    session = _build_session()
    _write_source_file(tmp_path, "receitas/arrecadacao-2025.xml")
    monkeypatch.setattr(empty_state_module, "get_cli_data_directory", lambda: tmp_path)

    suggestion = resolve_empty_result_suggestion(
        session,
        domain_key="receitas",
        filters={"ano": 2025, "tipo_de_dado": "arrecadacao"},
        default_suggestion="Nenhum registro de arrecadacoes encontrado com os filtros.",
    )

    assert suggestion == (
        "Os arquivos-fonte de arrecadacoes para 2025 existem no ambiente, mas esse dominio ainda nao foi "
        "importado no banco local. Reimporte a base SQLite antes de responder essa pergunta."
    )

    session.close()


def test_resolve_empty_result_suggestion_keeps_default_without_anchor_filters(
    monkeypatch,
    tmp_path,
) -> None:
    session = _build_session()
    _write_source_file(tmp_path, "despesas/empenhos/empenhos-2025.xml")
    monkeypatch.setattr(empty_state_module, "get_cli_data_directory", lambda: tmp_path)

    suggestion = resolve_empty_result_suggestion(
        session,
        domain_key="despesas",
        filters={"credor": "inexistente"},
        default_suggestion="Nenhuma despesa encontrada com os filtros.",
    )

    assert suggestion == "Nenhuma despesa encontrada com os filtros."

    session.close()


def test_resolve_empty_result_suggestion_keeps_default_when_scope_already_exists(
    monkeypatch,
    tmp_path,
) -> None:
    session = _build_session()
    session.add(
        ReceitaArrecadacao(
            exercicio=2025,
            mes="janeiro",
            data_arrecadacao=date(2025, 1, 10),
            unidade_gestora="PREFEITURA MUNICIPAL",
            fonte_recurso="livre",
            valor_previsto_bruto=1000,
            valor_arrecadado_bruto=900,
            valor_previsto_deducoes=0,
            valor_realizado_deducoes=0,
            valor_previsto_liquido=1000,
            valor_arrecadado_liquido=900,
        )
    )
    session.commit()
    _write_source_file(tmp_path, "receitas/arrecadacao-2025.xml")
    monkeypatch.setattr(empty_state_module, "get_cli_data_directory", lambda: tmp_path)

    suggestion = resolve_empty_result_suggestion(
        session,
        domain_key="receitas",
        filters={"ano": 2025, "tipo_de_dado": "arrecadacao"},
        default_suggestion="Nenhum registro de arrecadacoes encontrado com os filtros.",
    )

    assert suggestion == "Nenhum registro de arrecadacoes encontrado com os filtros."

    session.close()
