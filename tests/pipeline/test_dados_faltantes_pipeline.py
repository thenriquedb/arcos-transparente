from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, DespesaDocumento, Eleito, Patrimonio, QuadroPessoal
from ingestion.pipeline import IngestionPipeline


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
