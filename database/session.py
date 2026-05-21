"""Sessão e engine SQLAlchemy para SQLite."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database/transparencia.db")


engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Aplica pragmas para concorrência, integridade e performance em SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Fornece uma sessão com gerenciamento de fechamento."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
