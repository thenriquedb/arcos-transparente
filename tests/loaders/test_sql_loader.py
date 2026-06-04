from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Servidor
from ingestion.loaders.sql_loader import SQLLoader


def test_sql_loader_lida_com_duplicados_no_mesmo_batch_sem_rollback() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = session_local()

    loader = SQLLoader(session=session, batch_size=100)
    registros = [
        {
            "source_id": 101,
            "competencia_referencia": date(2026, 1, 1),
            "nome": "Maria da Silva",
            "cpf": "***345.678-**",
            "matricula": "90001-1",
            "cargo_funcao": "Enfermeira",
            "lotacao": "Secretaria de Saude",
        },
        {
            "source_id": 101,
            "competencia_referencia": date(2026, 1, 1),
            "nome": "Maria da Silva",
            "cpf": "***345.678-**",
            "matricula": "90001-1",
            "cargo_funcao": "Enfermeira",
            "lotacao": "Secretaria de Saude",
        },
    ]

    resultado = loader.load(registros, Servidor)

    assert resultado.inseridos == 1
    assert resultado.atualizados == 0
    assert resultado.ignorados == 1
    assert resultado.erros == 0
    assert session.query(Servidor).count() == 1

    session.close()


def test_sql_loader_sanitiza_campos_textuais_antes_de_persistir() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = session_local()

    loader = SQLLoader(session=session, batch_size=100)
    registros = [
        {
            "source_id": 202,
            "competencia_referencia": date(2026, 1, 1),
            "nome": "Maria\x00 da Silva",
            "cargo_funcao": "Enfermeira\x1f",
            "lotacao": "Secretaria\tde Saude\x00",
        }
    ]

    resultado = loader.load(registros, Servidor)
    servidor = session.query(Servidor).one()

    assert resultado.inseridos == 1
    assert resultado.erros == 0
    assert servidor.nome == "Maria da Silva"
    assert servidor.cargo_funcao == "Enfermeira"
    assert servidor.lotacao == "Secretaria\tde Saude"

    session.close()


def test_sql_loader_ignora_novo_servidor_com_matricula_ja_existente() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = session_local()

    loader = SQLLoader(session=session, batch_size=100)
    registros = [
        {
            "source_id": 301,
            "competencia_referencia": date(2026, 1, 1),
            "nome": "Maria da Silva",
            "cpf": "***345.678-**",
            "matricula": "90001-1",
            "cargo_funcao": "Enfermeira",
            "lotacao": "UPA Central",
        },
        {
            "source_id": 302,
            "competencia_referencia": date(2026, 1, 1),
            "nome": "Maria da Silva",
            "cpf": "***345.678-**",
            "matricula": "90001-1",
            "cargo_funcao": "Enfermeira Responsavel",
            "lotacao": "Hospital Municipal",
        },
    ]

    resultado = loader.load(registros, Servidor)

    assert resultado.inseridos == 1
    assert resultado.atualizados == 0
    assert resultado.ignorados == 1
    assert resultado.erros == 0

    servidor = session.query(Servidor).one()
    assert servidor.source_id == 301
    assert servidor.matricula == "90001-1"
    assert servidor.lotacao == "UPA Central"

    session.close()
