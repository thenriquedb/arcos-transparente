from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
)
from ingestion.parsers.xml.contratos_parser import ContratosParser
from ingestion.pipeline import IngestionPipeline


def test_load_contratos_persiste_campos_e_filhos_completos() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = session_local()

    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "contratos_sample.xml"
    )
    registros = ContratosParser().parse(str(fixture_path))

    pipeline = IngestionPipeline(data_dir="data/xml")
    resultado = pipeline._load_contratos(session=session, registros=registros)

    contrato = session.query(Contrato).filter(Contrato.numero == "001/2025").one()

    assert resultado.inseridos == 2
    assert contrato.numero_licitatorio == "123/2025"
    assert contrato.numero_instrumento == "001/2025"
    assert contrato.tipo_instrumento_contratual == "Contrato"
    assert contrato.possui_aditivo == "Nao"
    assert contrato.descricao_despesa == "Festividades e Homenagens"
    assert contrato.xml_original is not None
    assert "<InstrumentoContratual>" in contrato.xml_original
    assert (
        "<DescricaoDespesa>Festividades e Homenagens</DescricaoDespesa>"
        in contrato.xml_original
    )

    despesas = (
        session.query(ContratoDespesaOrcamentaria)
        .filter(ContratoDespesaOrcamentaria.contrato_id == contrato.id)
        .order_by(ContratoDespesaOrcamentaria.ordem.asc())
        .all()
    )
    itens = (
        session.query(ContratoItemAdquirido)
        .filter(ContratoItemAdquirido.contrato_id == contrato.id)
        .order_by(ContratoItemAdquirido.ordem.asc())
        .all()
    )

    assert len(despesas) == 2
    assert despesas[0].natureza_despesa_rubrica == "339039200000"
    assert float(despesas[0].valor_despesa) == 7500.0
    assert len(itens) == 1
    assert itens[0].numero_item == "2"
    assert float(itens[0].valor_total) == 10500.0

    session.close()
