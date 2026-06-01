from __future__ import annotations

from datetime import date
from decimal import Decimal

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
            "nome": "Maria da Silva",
            "cargo": "Enfermeira",
            "secretaria": "Secretaria de Saude",
            "salario_base": Decimal("2500.00"),
            "competencia_referencia": date(2025, 1, 1),
        },
        {
            "nome": "Maria da Silva",
            "cargo": "Enfermeira",
            "secretaria": "Secretaria de Saude",
            "salario_base": Decimal("2500.00"),
            "competencia_referencia": date(2025, 1, 1),
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
            "nome": "Maria\x00 da Silva",
            "cargo": "Enfermeira\x1f",
            "secretaria": "Secretaria\tde Saude\x00",
            "salario_base": Decimal("2500.00"),
            "competencia_referencia": date(2025, 1, 1),
        }
    ]

    resultado = loader.load(registros, Servidor)
    servidor = session.query(Servidor).one()

    assert resultado.inseridos == 1
    assert resultado.erros == 0
    assert servidor.nome == "Maria da Silva"
    assert servidor.cargo == "Enfermeira"
    assert servidor.secretaria == "Secretaria\tde Saude"

    session.close()
