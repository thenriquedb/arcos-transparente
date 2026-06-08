from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, EstoqueMaterial, EstoqueMovimentacao
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


def test_arquivos_por_tipo_estoques_inclui_apenas_xml_dedicados(tmp_path) -> None:
    estoques_dir = tmp_path / "administracao" / "estoques"
    estoques_dir.mkdir(parents=True)
    (estoques_dir / "estoque-prefeitura-2025.xml").write_text(
        (FIXTURES_DIR / "estoques_sample.xml").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )
    (estoques_dir / "administracaoEstoque.xml").write_text(
        (FIXTURES_DIR / "estoques_invalid_layout.xml").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )

    pipeline = IngestionPipeline(data_dir=str(tmp_path))

    arquivos = pipeline._arquivos_por_tipo("estoques", 2025)

    assert [arquivo.name for arquivo in arquivos] == ["estoque-prefeitura-2025.xml"]


def test_pipeline_importa_e_reimporta_estoques_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    estoques_dir = tmp_path / "administracao" / "estoques"
    estoques_dir.mkdir(parents=True)
    (estoques_dir / "estoque-saude-2025.xml").write_text(
        '<?xml version="1.0" encoding="ISO-8859-1"?><ESTOQUE/>',
        encoding="utf-8",
    )
    arquivo = estoques_dir / "estoque-prefeitura-2025.xml"
    arquivo.write_text(
        (FIXTURES_DIR / "estoques_sample.xml").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado_inicial = pipeline.run(tipos=["estoques"], ano=2025)

    assert resultado_inicial["estoques"].inseridos == 2
    assert session.query(EstoqueMaterial).count() == 2
    assert session.query(EstoqueMovimentacao).count() == 3

    luva = (
        session.query(EstoqueMaterial)
        .filter(EstoqueMaterial.material == "LUVA DESCARTAVEL")
        .one()
    )
    assert luva.saldo_valor == Decimal("220.0000")
    assert len(luva.movimentacoes) == 3
    assert luva.movimentacoes[0].valor_total == Decimal("40.0000")
    session.rollback()

    atualizado = (
        (FIXTURES_DIR / "estoques_sample.xml")
        .read_text(encoding="utf-8")
        .replace("<SaldoValor>220.0000</SaldoValor>", "<SaldoValor>250.0000</SaldoValor>", 1)
        .replace("<ValorTotal>40.0000</ValorTotal>", "<ValorTotal>45.0000</ValorTotal>", 1)
    )
    arquivo.write_text(atualizado, encoding="ISO-8859-1")

    resultado_reimportado = pipeline.run(tipos=["estoques"], ano=2025)

    assert resultado_reimportado["estoques"].atualizados == 1
    assert resultado_reimportado["estoques"].ignorados == 1
    assert session.query(EstoqueMaterial).count() == 2
    assert session.query(EstoqueMovimentacao).count() == 3

    luva_atualizada = (
        session.query(EstoqueMaterial)
        .filter(EstoqueMaterial.material == "LUVA DESCARTAVEL")
        .one()
    )
    alcool = (
        session.query(EstoqueMaterial)
        .filter(EstoqueMaterial.material == "ALCOOL 70")
        .one()
    )
    assert alcool.saldo_valor == Decimal("120.0000")
    assert luva_atualizada.saldo_valor == Decimal("250.0000")
    assert luva_atualizada.movimentacoes[0].valor_total == Decimal("45.0000")

    session.close()
