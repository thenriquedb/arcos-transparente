from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, DespesaPorFuncao
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


def test_arquivos_por_tipo_despesas_inclui_csv_de_despesas_por_funcao(tmp_path) -> None:
    relatorio_dir = tmp_path / "despesas" / "despesas-por-funcao"
    relatorio_dir.mkdir(parents=True)
    (relatorio_dir / "despesas-por-funcao-prefeitura-2025.csv").write_text(
        (FIXTURES_DIR / "despesas_por_funcao_sample.csv").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )

    pipeline = IngestionPipeline(data_dir=str(tmp_path))

    arquivos = pipeline._arquivos_por_tipo("despesas", 2025)

    assert "despesas-por-funcao-prefeitura-2025.csv" in [a.name for a in arquivos]


def test_pipeline_importa_e_reimporta_despesas_por_funcao_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    relatorio_dir = tmp_path / "despesas" / "despesas-por-funcao"
    relatorio_dir.mkdir(parents=True)
    arquivo = relatorio_dir / "despesas-por-funcao-prefeitura-2025.csv"
    arquivo.write_text(
        (FIXTURES_DIR / "despesas_por_funcao_sample.csv").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado_inicial = pipeline.run(tipos=["despesas"], ano=2025)

    assert resultado_inicial["despesas"].inseridos == 2
    assert session.query(DespesaPorFuncao).count() == 2

    saude = (
        session.query(DespesaPorFuncao).filter(DespesaPorFuncao.funcao == "Saude").one()
    )
    assert saude.valor_pago == Decimal("73415583.84")
    assert saude.linha_origem == 6
    session.rollback()

    atualizado = (
        (FIXTURES_DIR / "despesas_por_funcao_sample.csv")
        .read_text(encoding="utf-8")
        .replace('="R$ 73.415.583,84"', '="R$ 70.000.000,00"', 1)
    )
    arquivo.write_text(atualizado, encoding="ISO-8859-1")

    resultado_reimportado = pipeline.run(tipos=["despesas"], ano=2025)

    assert resultado_reimportado["despesas"].atualizados == 1
    assert resultado_reimportado["despesas"].ignorados == 1
    assert session.query(DespesaPorFuncao).count() == 2

    saude_atualizada = (
        session.query(DespesaPorFuncao).filter(DespesaPorFuncao.funcao == "Saude").one()
    )
    assert saude_atualizada.valor_pago == Decimal("70000000.00")

    session.close()
