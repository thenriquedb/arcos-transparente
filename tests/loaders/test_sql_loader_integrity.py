"""Integridade transacional, isolamento de erro e validação de tipos do SQLLoader.

Cobre o núcleo ACID de toda importação (`ingestion/loaders/sql_loader.py`):
- divisão em batches e isolamento de registro inválido dentro do batch;
- rollback do batch inteiro em falha de banco;
- o "type firewall" de `_normalize_and_validate`;
- o branch de update vs. ignorado;
- as guardas de unique constraint.

Usa modelos de teste dedicados (não modelos da aplicação) para isolar o
comportamento do loader da evolução do schema real.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint, create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ingestion.loaders.sql_loader import SQLLoader


class _Base(DeclarativeBase):
    pass


class _Widget(_Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    data: Mapped[date | None] = mapped_column(Date, nullable=True)
    nome: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (UniqueConstraint("codigo", name="uq_widget_codigo"),)


class _NoUnique(_Base):
    __tablename__ = "no_unique"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), nullable=False)


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    _Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _widget(codigo: str, **extra) -> dict:
    return {"codigo": codigo, "valor": None, "data": None, "nome": None, **extra}


# --- Batches e persistência -------------------------------------------------


def test_carrega_registros_em_multiplos_batches() -> None:
    session = _build_session()
    loader = SQLLoader(session=session, batch_size=100)

    registros = [_widget(f"W{i:04d}") for i in range(250)]
    resultado = loader.load(registros, _Widget)

    assert (resultado.inseridos, resultado.atualizados, resultado.ignorados, resultado.erros) == (250, 0, 0, 0)
    assert session.scalar(select(func.count()).select_from(_Widget)) == 250

    session.close()


# --- Isolamento de erro por registro ----------------------------------------


def test_registro_invalido_nao_aborta_o_resto_do_batch() -> None:
    session = _build_session()
    loader = SQLLoader(session=session, batch_size=100)

    registros = [
        _widget("OK-1"),
        {"valor": None, "data": None, "nome": "sem codigo"},  # falta `codigo` obrigatório
        _widget("OK-2"),
    ]
    resultado = loader.load(registros, _Widget)

    # O registro inválido vira erro; os válidos continuam persistidos no mesmo batch.
    assert resultado.inseridos == 2
    assert resultado.erros == 1
    persistidos = {w.codigo for w in session.execute(select(_Widget)).scalars()}
    assert persistidos == {"OK-1", "OK-2"}

    session.close()


# --- Update vs. ignorado ----------------------------------------------------


def test_atualiza_apenas_quando_ha_mudanca_real() -> None:
    session = _build_session()
    loader = SQLLoader(session=session, batch_size=100)

    # Cargas consecutivas: cada `load()` abre e fecha sua própria transação, então
    # não há consulta intercalada deixando uma transação aberta na sessão.
    r_insert = loader.load([_widget("A", nome="Maria")], _Widget)
    r_update = loader.load([_widget("A", nome="Maria Silva")], _Widget)  # campo não-único alterado
    r_ignore = loader.load([_widget("A", nome="Maria Silva")], _Widget)  # reimportação idêntica

    assert r_insert.inseridos == 1
    assert (r_update.inseridos, r_update.atualizados, r_update.ignorados) == (0, 1, 0)
    assert (r_ignore.inseridos, r_ignore.atualizados, r_ignore.ignorados) == (0, 0, 1)
    assert session.execute(select(_Widget).where(_Widget.codigo == "A")).scalar_one().nome == "Maria Silva"

    session.close()


def test_apply_updates_detecta_mudanca_de_campo() -> None:
    instancia = _Widget(codigo="A", nome="X")

    assert SQLLoader._apply_updates(instancia, {"nome": "Y"}) is True
    assert instancia.nome == "Y"
    assert SQLLoader._apply_updates(instancia, {"nome": "Y"}) is False


# --- Type firewall (_normalize_and_validate) --------------------------------


def test_normalize_and_validate_aceita_e_coage_valores_validos() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    payload = loader._normalize_and_validate(
        {"codigo": "A", "valor": 10, "data": "2025-01-31", "nome": "Maria"},
        _Widget,
    )

    assert payload["codigo"] == "A"
    assert payload["valor"] == Decimal(10)
    assert payload["data"] == date(2025, 1, 31)
    assert payload["nome"] == "Maria"


def test_normalize_and_validate_rejeita_valor_monetario_em_string() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(TypeError, match="Campo monetario deve ser Decimal/int, nao string"):
        loader._normalize_and_validate(_widget("A", valor="10.50"), _Widget)


def test_normalize_and_validate_rejeita_valor_monetario_float() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    # Float é proibido em moeda (precisão binária); só Decimal/int passam.
    with pytest.raises(TypeError, match="Campo monetario invalido"):
        loader._normalize_and_validate(_widget("A", valor=10.5), _Widget)


def test_normalize_and_validate_rejeita_data_de_tipo_invalido() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(TypeError, match="Campo data invalido"):
        loader._normalize_and_validate(_widget("A", data=20250131), _Widget)


def test_normalize_and_validate_rejeita_texto_de_tipo_invalido() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(TypeError, match="Campo textual invalido"):
        loader._normalize_and_validate(_widget("A", nome=123), _Widget)


def test_normalize_and_validate_rejeita_campo_obrigatorio_ausente() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(ValueError, match="Campo obrigatorio ausente: codigo"):
        loader._normalize_and_validate({"valor": None, "data": None, "nome": None}, _Widget)


def test_normalize_and_validate_rejeita_campo_obrigatorio_nulo() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(ValueError, match="Campo obrigatorio nulo: codigo"):
        loader._normalize_and_validate(_widget(None), _Widget)  # type: ignore[arg-type]


# --- Guardas de unique constraint -------------------------------------------


def test_build_unique_filter_exige_unique_constraint_no_modelo() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(ValueError, match="sem UniqueConstraint"):
        loader._build_unique_filter({"nome": "x"}, _NoUnique)


def test_build_unique_filter_exige_campo_unico_no_payload() -> None:
    loader = SQLLoader(session=_build_session(), batch_size=100)

    with pytest.raises(ValueError, match="Campo unico ausente no payload: codigo"):
        loader._build_unique_filter({"valor": None}, _Widget)


# --- Rollback de batch em falha de banco ------------------------------------


class _DbFailsAtBegin:
    """Sessão fake cujo `begin()` falha — simula falha de banco (ex.: database is locked)."""

    def __init__(self) -> None:
        self.rollback_calls = 0

    def begin(self):
        raise SQLAlchemyError("database is locked")

    def rollback(self) -> None:
        self.rollback_calls += 1


def test_rollback_do_batch_inteiro_em_falha_de_banco() -> None:
    session = _DbFailsAtBegin()
    loader = SQLLoader(session=session, batch_size=100)

    registros = [_widget("A"), _widget("B"), _widget("C")]
    resultado = loader.load(registros, _Widget)

    # Batch inteiro contabilizado como erro, rollback chamado, nada inserido.
    assert resultado.erros == len(registros)
    assert resultado.inseridos == 0
    assert session.rollback_calls == 1
