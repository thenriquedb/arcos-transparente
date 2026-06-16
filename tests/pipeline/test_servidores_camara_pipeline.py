from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, SalarioPorCargoCamara, ServidorCamara
from ingestion.pipeline import IngestionPipeline


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return session_local()


def _write_camara_csv(path, competencia: str = "01/2026", rows: list[str] | None = None) -> None:
    header = "Nome; Matrícula; Cargo; Lotação; Vínculo; Situação; Admissão; Salário Base; Proventos; Vantagens; Proventos Totais; Descontos; Líquido"
    default_rows = [
        "Virginia Oliveira de Sousa;1600/1;ADVOGADO;Secretaria da Camara;;Em atividade;27/04/2016;6181.74;8530.79;0.00;8530.79;2035.61;6495.18",
    ]
    lines = [
        f"Cidade360 - Transparência Brasil - Camara Municipal de Arcos - {competencia}",
        header,
        *(rows or default_rows),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def test_pipeline_descobre_csv_de_servidores_camara(tmp_path) -> None:
    servidores_dir = tmp_path / "servidores"
    servidores_dir.mkdir(parents=True)
    csv_path = servidores_dir / "servidores-camara-2026.csv"
    _write_camara_csv(csv_path)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    discovered = pipeline._arquivos_por_tipo("servidores_camara", None)

    assert discovered == [csv_path]


def test_pipeline_importa_e_reimporta_servidores_camara_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    servidores_dir = tmp_path / "servidores"
    servidores_dir.mkdir(parents=True)
    csv_path = servidores_dir / "servidores-camara-2026.csv"
    _write_camara_csv(csv_path)

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado = pipeline.run(tipos=["servidores_camara"], ano=2026)

    assert resultado["servidores_camara"].inseridos == 1
    assert session.query(ServidorCamara).count() == 1

    servidor = session.query(ServidorCamara).one()
    assert servidor.matricula == "1600/1"
    assert servidor.nome == "Virginia Oliveira de Sousa"
    assert servidor.competencia_referencia == date(2026, 1, 1)

    session.rollback()

    resultado2 = pipeline.run(tipos=["servidores_camara"], ano=2026)
    assert resultado2["servidores_camara"].atualizados + resultado2["servidores_camara"].ignorados == 1
    assert session.query(ServidorCamara).count() == 1

    session.close()


def test_pipeline_filtra_por_ano_servidores_camara(tmp_path) -> None:
    servidores_dir = tmp_path / "servidores"
    servidores_dir.mkdir(parents=True)

    (servidores_dir / "servidores-camara-2025.csv").write_text(
        "Cidade360 - Transparência Brasil - Camara Municipal de Arcos - 01/2025\n"
        "Nome; Matrícula; Cargo; Lotação; Vínculo; Situação; Admissão; Salário Base; Proventos; Vantagens; Proventos Totais; Descontos; Líquido\n",
        encoding="utf-8",
    )
    (servidores_dir / "servidores-camara-2026.csv").write_text(
        "Cidade360 - Transparência Brasil - Camara Municipal de Arcos - 01/2026\n"
        "Nome; Matrícula; Cargo; Lotação; Vínculo; Situação; Admissão; Salário Base; Proventos; Vantagens; Proventos Totais; Descontos; Líquido\n",
        encoding="utf-8",
    )

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    discovered = pipeline._arquivos_por_tipo("servidores_camara", 2025)

    assert len(discovered) == 1
    assert "2025" in discovered[0].name


def test_pipeline_importa_salario_por_cargo_camara(monkeypatch, tmp_path) -> None:
    servidores_dir = tmp_path / "servidores"
    servidores_dir.mkdir(parents=True)

    csv_path = servidores_dir / "salarios-por-cargo-camara-2026.csv"
    csv_path.write_text(
        '="Filtros Utilizados"\n'
        '="Vínculo";="TODOS";="Unidade";="CÂMARA MUNICIPAL DE ARCOS"\n'
        '="Mês";="01/2026";="";=""\n'
        '="Tabela de Remuneração dos Cargos e Funções"\n'
        '="Código";="Descrição do Cargo"\n'
        '="22";="ADVOGADO"\n'
        '="1";="Vereador"\n'
        '="PRONIM TB - 16/06/2026 - Pessoal"\n',
        encoding="utf-8",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado = pipeline.run(tipos=["salario_por_cargo_camara"])

    assert resultado["salario_por_cargo_camara"].inseridos == 2
    assert session.query(SalarioPorCargoCamara).count() == 2

    advogado = session.query(SalarioPorCargoCamara).filter_by(codigo="22").one()
    assert advogado.descricao == "ADVOGADO"
    assert advogado.competencia_referencia == date(2026, 1, 1)

    session.close()
