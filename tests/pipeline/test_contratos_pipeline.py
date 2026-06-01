from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
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


def test_pipeline_contratos_nao_persiste_caracteres_invalidos(
    monkeypatch, tmp_path
) -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    session = session_local()

    contratos_dir = tmp_path / "administracao"
    contratos_dir.mkdir(parents=True)
    (contratos_dir / "contratos-2025.xml").write_text(
        """<?xml version="1.0" encoding="ISO-8859-1"?>
<Root>
    <InstrumentoContratual>
        <NumeroLicitatorio>123/2025</NumeroLicitatorio>
        <TipoInstrumentoContratual>Contrato</TipoInstrumentoContratual>
        <NumeroInstrumentoContratual>001/2025</NumeroInstrumentoContratual>
        <NomeFornecedor>Fornecedor\x00 Alfa</NomeFornecedor>
        <CNPJFornecedor>12.345.678/0001-99</CNPJFornecedor>
        <ValorInstrumentoContratual>R$ 10.500,00</ValorInstrumentoContratual>
        <DataEmissao>10/01/2025</DataEmissao>
        <DataExpiracao>10/01/2026</DataExpiracao>
        <TipoContrato>Prestação\x1f de Serviço</TipoContrato>
        <UnidadeGestora>Secretaria de Saúde</UnidadeGestora>
        <PossuiAditivo>Não</PossuiAditivo>
        <Objeto>Locação\x00 de estrutura</Objeto>
        <DespesasOrcamentarias>
            <DespesaOrcamentaria>
                <DescricaoDespesa>Festividades\x1f e Homenagens</DescricaoDespesa>
                <ValorDespesa>R$ 7.500,00</ValorDespesa>
            </DespesaOrcamentaria>
        </DespesasOrcamentarias>
        <ItensAdquiridos>
            <Item>
                <Identificacao>Estrutura\x00 de evento</Identificacao>
                <Quantidade>2.0000</Quantidade>
                <ValorUnitario>R$ 5.250,00</ValorUnitario>
                <ValorTotal>R$ 10.500,00</ValorTotal>
            </Item>
        </ItensAdquiridos>
    </InstrumentoContratual>
</Root>
""",
        encoding="ISO-8859-1",
    )

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    resultado = IngestionPipeline(data_dir=str(tmp_path)).run(
        tipos=["contratos"],
        ano=2025,
    )
    contrato = session.query(Contrato).one()
    despesa = session.query(ContratoDespesaOrcamentaria).one()
    item = session.query(ContratoItemAdquirido).one()

    assert resultado["contratos"].inseridos == 1
    assert contrato.fornecedor == "Fornecedor Alfa"
    assert contrato.categoria == "Prestação de Serviço"
    assert contrato.descricao == "Locação de estrutura"
    assert "\x00" not in contrato.xml_original
    assert "\x1f" not in contrato.xml_original
    assert despesa.descricao_despesa == "Festividades e Homenagens"
    assert item.identificacao == "Estrutura de evento"

    session.close()
