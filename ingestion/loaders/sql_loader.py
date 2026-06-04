"""Loader SQL para persistência de registros parseados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from loguru import logger
from sqlalchemy import Date, Numeric, String, Text, and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import UniqueConstraint

from database.models import Servidor
from ingestion.parsers.xml.shared import sanitize_xml_payload


@dataclass
class LoadResult:
    """Resultado agregado de carga SQL."""

    inseridos: int = 0
    atualizados: int = 0
    ignorados: int = 0
    erros: int = 0


class SQLLoader:
    """Persistência com upsert, validação e batching."""

    def __init__(self, session: Session, batch_size: int = 100) -> None:
        """Inicializa loader para uma sessão SQLAlchemy."""
        self.session = session
        self.batch_size = batch_size

    def load(self, registros: list[dict[str, Any]], modelo: type) -> LoadResult:
        """Carrega registros no banco com upsert por índice único composto."""
        resultado = LoadResult()
        if not registros:
            return resultado

        for inicio in range(0, len(registros), self.batch_size):
            batch = registros[inicio : inicio + self.batch_size]
            try:
                with self.session.begin():
                    for registro in batch:
                        try:
                            payload = self._normalize_and_validate(registro, modelo)
                            unique_filter = self._build_unique_filter(payload, modelo)
                            existente = self.session.execute(
                                select(modelo).where(and_(*unique_filter))
                            ).scalar_one_or_none()

                            if existente is None:
                                if duplicate := self._find_duplicate_before_insert(
                                    payload,
                                    modelo,
                                ):
                                    resultado.ignorados += 1
                                    logger.warning(
                                        f"Ignorado (matricula ja cadastrada) em {modelo.__tablename__}: {payload}"
                                    )
                                    continue
                                self.session.add(modelo(**payload))
                                # Flush garante que registros novos fiquem visiveis
                                # para o restante do batch e evita violacao de unique
                                # constraint quando o mesmo item aparece repetido.
                                self.session.flush()
                                resultado.inseridos += 1
                                logger.info(
                                    f"Inserido em {modelo.__tablename__}: {payload}"
                                )
                                continue

                            alterou = self._apply_updates(existente, payload)
                            if alterou:
                                resultado.atualizados += 1
                                logger.info(
                                    f"Atualizado em {modelo.__tablename__}: {payload}"
                                )
                            else:
                                resultado.ignorados += 1
                                logger.warning(
                                    f"Ignorado (sem alteracao) em {modelo.__tablename__}: {payload}"
                                )

                        except Exception as exc:  # noqa: BLE001
                            resultado.erros += 1
                            logger.error(
                                f"Falha ao processar registro em {modelo.__tablename__}: {registro}. Erro: {exc}"
                            )
            except SQLAlchemyError as exc:
                self.session.rollback()
                resultado.erros += len(batch)
                logger.error(
                    f"Rollback de batch em {modelo.__tablename__}. Erro: {exc}"
                )

        return resultado

    def _build_unique_filter(self, payload: dict[str, Any], modelo: type) -> list[Any]:
        """Monta filtros SQL a partir da unique constraint composta do modelo."""
        unique_constraint: Optional[UniqueConstraint] = None
        for constraint in modelo.__table__.constraints:
            if isinstance(constraint, UniqueConstraint):
                unique_constraint = constraint
                break

        if unique_constraint is None:
            raise ValueError(
                f"Modelo {modelo.__name__} sem UniqueConstraint para upsert"
            )

        filters: list[Any] = []
        for col in unique_constraint.columns:
            if col.name not in payload:
                raise ValueError(f"Campo unico ausente no payload: {col.name}")
            filters.append(getattr(modelo, col.name) == payload[col.name])
        return filters

    def _normalize_and_validate(
        self, registro: dict[str, Any], modelo: type
    ) -> dict[str, Any]:
        """Normaliza e valida tipos de acordo com colunas do modelo."""
        registro = sanitize_xml_payload(registro)
        payload: dict[str, Any] = {}
        for coluna in modelo.__table__.columns:
            if coluna.name in {"id", "criado_em", "atualizado_em"}:
                continue
            if coluna.name not in registro:
                if not coluna.nullable:
                    raise ValueError(f"Campo obrigatorio ausente: {coluna.name}")
                payload[coluna.name] = None
                continue

            valor = registro[coluna.name]
            if valor is None:
                if not coluna.nullable:
                    raise ValueError(f"Campo obrigatorio nulo: {coluna.name}")
                payload[coluna.name] = None
                continue

            if isinstance(coluna.type, Numeric):
                if isinstance(valor, str):
                    raise TypeError(
                        f"Campo monetario deve ser Decimal/int, nao string: {coluna.name}"
                    )
                if not isinstance(valor, (Decimal, int)):
                    raise TypeError(f"Campo monetario invalido: {coluna.name}")
                payload[coluna.name] = Decimal(valor)
                continue

            if isinstance(coluna.type, Date):
                if isinstance(valor, str):
                    payload[coluna.name] = date.fromisoformat(valor)
                elif isinstance(valor, date):
                    payload[coluna.name] = valor
                else:
                    raise TypeError(f"Campo data invalido: {coluna.name}")
                continue

            if isinstance(coluna.type, (String, Text)):
                if not isinstance(valor, str):
                    raise TypeError(f"Campo textual invalido: {coluna.name}")
                payload[coluna.name] = valor
                continue

            payload[coluna.name] = valor

        return payload

    def _find_duplicate_before_insert(
        self,
        payload: dict[str, Any],
        modelo: type,
    ) -> Any | None:
        """Aplica regras de deduplicacao que nao devem virar upsert."""
        if modelo is not Servidor:
            return None

        matricula = payload.get("matricula")
        if not matricula:
            return None

        return self.session.execute(
            select(Servidor).where(Servidor.matricula == matricula)
        ).scalar_one_or_none()

    @staticmethod
    def _apply_updates(instancia: Any, payload: dict[str, Any]) -> bool:
        """Atualiza apenas campos alterados na instância existente."""
        mudou = False
        for chave, valor in payload.items():
            atual = getattr(instancia, chave)
            if atual != valor:
                setattr(instancia, chave, valor)
                mudou = True
        return mudou
