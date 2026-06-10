from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, EmendaParlamentar, TransferenciaFinanceiraMovimento
from ingestion.pipeline import IngestionPipeline


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


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


def test_pipeline_importa_e_reimporta_transferencias_financeiras_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    transferencias_dir = tmp_path / "transferencias-financeiras"
    transferencias_dir.mkdir(parents=True)
    xml_arquivo = transferencias_dir / "recebimentos-2026.xml"
    csv_arquivo = transferencias_dir / "emendas-parlamentares-2026.csv"

    xml_arquivo.write_text(
        (FIXTURES_DIR / "transferencias_financeiras_sample.xml").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )
    csv_arquivo.write_text(
        (FIXTURES_DIR / "emendas_parlamentares_sample.csv").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado_inicial = pipeline.run(tipos=["transferencias_financeiras"], ano=None)

    assert resultado_inicial["transferencias_financeiras"].inseridos == 5
    assert session.query(TransferenciaFinanceiraMovimento).count() == 2
    assert session.query(EmendaParlamentar).count() == 3
    session.rollback()

    xml_atualizado = xml_arquivo.read_text(encoding="ISO-8859-1").replace(
        "R$ 552.500,00",
        "R$ 600.000,00",
        2,
    )
    csv_atualizado = csv_arquivo.read_text(encoding="ISO-8859-1").replace(
        "R$ 750.000,00",
        "R$ 800.000,00",
        1,
    )
    xml_arquivo.write_text(xml_atualizado, encoding="ISO-8859-1")
    csv_arquivo.write_text(csv_atualizado, encoding="ISO-8859-1")

    resultado_reimportado = pipeline.run(tipos=["transferencias_financeiras"], ano=None)

    assert resultado_reimportado["transferencias_financeiras"].atualizados == 2
    assert resultado_reimportado["transferencias_financeiras"].ignorados == 3
    assert session.query(TransferenciaFinanceiraMovimento).count() == 2
    assert session.query(EmendaParlamentar).count() == 3

    movimento_atualizado = (
        session.query(TransferenciaFinanceiraMovimento)
        .filter(TransferenciaFinanceiraMovimento.sequencia_origem == 2)
        .one()
    )
    emenda_atualizada = session.query(EmendaParlamentar).filter(EmendaParlamentar.sequencia_origem == 3).one()

    assert movimento_atualizado.valor_movimento == Decimal("600000.00")
    assert movimento_atualizado.programacao_inicial == Decimal("600000.00")
    assert emenda_atualizada.valor == Decimal("800000.00")

    session.close()
