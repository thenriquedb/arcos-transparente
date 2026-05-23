from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Servidor
from ingestion.pipeline import IngestionPipeline


def test_find_servidor_canonico_prioriza_competencia_mais_recente() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = session_local()

    servidor_antigo = Servidor(
        nome="Maria da Silva",
        cargo="Enfermeira",
        secretaria="Secretaria de Saude",
        salario_base=2500,
        competencia_referencia=date(2025, 1, 1),
    )
    servidor_recente = Servidor(
        nome="Maria da Silva",
        cargo="Enfermeira",
        secretaria="Secretaria de Saude",
        salario_base=2700,
        competencia_referencia=date(2025, 3, 1),
    )
    session.add_all([servidor_antigo, servidor_recente])
    session.commit()

    encontrado = IngestionPipeline._find_servidor_canonico(
        session=session,
        nome="Maria da Silva",
        cargo="Enfermeira",
        secretaria="Secretaria de Saude",
    )

    assert encontrado is not None
    assert encontrado.competencia_referencia == date(2025, 3, 1)

    session.close()
