from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, DespesaDocumento, Eleito, Patrimonio, QuadroPessoal
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


def test_pipeline_importa_despesas_patrimonios_e_quadro_pessoal(
    monkeypatch,
    tmp_path,
) -> None:
    despesas_dir = tmp_path / "despesas" / "empenhos"
    patrimonios_dir = tmp_path / "administracao" / "patrimonios"
    quadro_dir = tmp_path / "servidores" / "quadro-pessoal"
    eleitos_dir = tmp_path / "camara"
    despesas_dir.mkdir(parents=True)
    patrimonios_dir.mkdir(parents=True)
    quadro_dir.mkdir(parents=True)
    eleitos_dir.mkdir(parents=True)

    (despesas_dir / "empenhos-2025.xml").write_text(
        """<?xml version="1.0" encoding="ISO-8859-1"?>
<Empenhos><Principal>
<Exercicio>2025</Exercicio><UnidadeGestora>CÂMARA MUNICIPAL</UnidadeGestora>
<NumeroEmpenho>000331</NumeroEmpenho><DataEmissaoEmpenho>17/09/2025</DataEmissaoEmpenho>
<Credor>EDISON DOS SANTOS</Credor><ValorPago>R$ 18,00</ValorPago>
</Principal></Empenhos>
""",
        encoding="ISO-8859-1",
    )
    (patrimonios_dir / "patrimonio-2025.xml").write_text(
        """<?xml version="1.0" encoding="ISO-8859-1"?>
<Patrimonios><ITEM>
<UnidadeGestora>PREFEITURA MUNICIPAL</UnidadeGestora><PLACA>27982</PLACA>
<DESCRICAOITEM>REFRIGERADOR</DESCRICAOITEM><VALORATUALIZADO>1995.0000</VALORATUALIZADO>
</ITEM></Patrimonios>
""",
        encoding="ISO-8859-1",
    )
    (quadro_dir / "quadro-pessoal-prefeitura-2025.xml").write_text(
        """<?xml version="1.0" encoding="ISO-8859-1"?>
<QuadroPessoais><QuadroPessoal>
<Competencia>01/2025</Competencia><RegimeContratacao>Comissionado</RegimeContratacao>
<VagasCriadas>62</VagasCriadas><VagasPreenchidas>77</VagasPreenchidas>
</QuadroPessoal></QuadroPessoais>
""",
        encoding="ISO-8859-1",
    )
    (eleitos_dir / "eleitos.xml").write_text(
        """<?xml version="1.0" encoding="ISO-8859-1"?>
<transparencia>
<vereadores municipio="Arcos" estado="MG"><vereador id="1">
<nomeCompleto>Maria Silva</nomeCompleto><partido>PL</partido>
<mandatos><mandato><inicio>2025</inicio><fim>2028</fim><status>em exercício</status></mandato></mandatos>
</vereador></vereadores>
</transparencia>
""",
        encoding="ISO-8859-1",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    resultado = IngestionPipeline(data_dir=str(tmp_path)).run(
        tipos=["despesas", "patrimonios", "quadro_pessoal", "eleitos"],
        ano=None,
    )

    assert resultado["despesas"].inseridos == 1
    assert resultado["patrimonios"].inseridos == 1
    assert resultado["quadro_pessoal"].inseridos == 1
    assert resultado["eleitos"].inseridos == 1
    assert session.query(DespesaDocumento).count() == 1
    assert session.query(Patrimonio).count() == 1
    assert session.query(QuadroPessoal).count() == 1
    assert session.query(Eleito).count() == 1

    session.close()


def test_pipeline_importa_e_reimporta_diarias_csv_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    diarias_dir = tmp_path / "despesas" / "diarias"
    diarias_dir.mkdir(parents=True)
    arquivo = diarias_dir / "diarias-camara-2025.csv"
    arquivo.write_text(
        (FIXTURES_DIR / "diarias_camara_sample.csv").read_text(encoding="utf-8"),
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
    assert session.query(DespesaDocumento).count() == 2

    primeiro = (
        session.query(DespesaDocumento)
        .filter(DespesaDocumento.tipo_origem == "diaria")
        .order_by(DespesaDocumento.sequencia_origem.asc())
        .first()
    )
    assert primeiro is not None
    assert primeiro.periodo_referencia_inicio.isoformat() == "2025-01-01"
    assert primeiro.periodo_referencia_fim.isoformat() == "2025-12-31"
    session.rollback()

    atualizado = (
        (FIXTURES_DIR / "diarias_camara_sample.csv")
        .read_text(encoding="utf-8")
        .replace('="R$ 4.128,00"', '="R$ 5.000,00"', 1)
        .replace('="R$ 4.128,00"', '="R$ 5.000,00"', 1)
        .replace('="R$ 4.128,00"', '="R$ 5.000,00"', 1)
    )
    arquivo.write_text(atualizado, encoding="ISO-8859-1")

    resultado_reimportado = pipeline.run(tipos=["despesas"], ano=2025)

    assert resultado_reimportado["despesas"].atualizados == 1
    assert resultado_reimportado["despesas"].ignorados == 1
    assert session.query(DespesaDocumento).count() == 2

    atualizado_primeiro = (
        session.query(DespesaDocumento)
        .filter(
            DespesaDocumento.tipo_origem == "diaria",
            DespesaDocumento.sequencia_origem == 1,
        )
        .one()
    )
    assert atualizado_primeiro.valor_empenhado == Decimal("5000.00")
    assert atualizado_primeiro.valor_liquidado == Decimal("5000.00")
    assert atualizado_primeiro.valor_pago == Decimal("5000.00")

    session.close()


def test_pipeline_importa_e_reimporta_passagens_csv_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    passagens_dir = tmp_path / "despesas" / "passagens"
    passagens_dir.mkdir(parents=True)
    arquivo = passagens_dir / "passagens-2026.csv"
    arquivo.write_text(
        (FIXTURES_DIR / "passagens_camara_sample.csv").read_text(encoding="utf-8"),
        encoding="ISO-8859-1",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado_inicial = pipeline.run(tipos=["despesas"], ano=2026)

    assert resultado_inicial["despesas"].inseridos == 2
    assert session.query(DespesaDocumento).count() == 2

    primeiro = (
        session.query(DespesaDocumento)
        .filter(DespesaDocumento.tipo_origem == "passagem")
        .order_by(DespesaDocumento.sequencia_origem.asc())
        .first()
    )
    assert primeiro is not None
    assert primeiro.periodo_referencia_inicio.isoformat() == "2026-01-01"
    assert primeiro.periodo_referencia_fim.isoformat() == "2026-06-30"
    assert primeiro.categoria_documento == "PASSAGENS E DESPESAS COM LOCOMOCAO"
    session.rollback()

    atualizado = (
        (FIXTURES_DIR / "passagens_camara_sample.csv")
        .read_text(encoding="utf-8")
        .replace('="R$ 1.500,09"', '="R$ 1.900,09"', 1)
        .replace('="R$ 1.500,09"', '="R$ 1.900,09"', 1)
    )
    arquivo.write_text(atualizado, encoding="ISO-8859-1")

    resultado_reimportado = pipeline.run(tipos=["despesas"], ano=2026)

    assert resultado_reimportado["despesas"].atualizados == 1
    assert resultado_reimportado["despesas"].ignorados == 1
    assert session.query(DespesaDocumento).count() == 2

    atualizado_primeiro = (
        session.query(DespesaDocumento)
        .filter(
            DespesaDocumento.tipo_origem == "passagem",
            DespesaDocumento.sequencia_origem == 1,
        )
        .one()
    )
    assert atualizado_primeiro.valor_liquidado == Decimal("1900.09")
    assert atualizado_primeiro.valor_pago == Decimal("1900.09")

    session.close()
