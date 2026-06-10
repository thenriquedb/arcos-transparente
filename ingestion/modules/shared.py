"""Shared helpers for ingestion adapters and tipo-specific loaders."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ingestion.loaders.sql_loader import LoadResult

UpsertStatus = Literal["inserted", "updated", "ignored"]


def merge_load_results(target: LoadResult, partial: LoadResult) -> None:
    """Accumulate file-level or child loader results into one report."""

    target.inseridos += partial.inseridos
    target.atualizados += partial.atualizados
    target.ignorados += partial.ignorados
    target.erros += partial.erros


def apply_upsert_status(result: LoadResult, status: UpsertStatus) -> None:
    """Translate an upsert outcome into the shared reporting counters."""

    if status == "inserted":
        result.inseridos += 1
        return
    if status == "updated":
        result.atualizados += 1
        return
    result.ignorados += 1


def apply_payload_updates(instance: Any, payload: dict[str, Any]) -> bool:
    """Update only changed fields and report whether anything changed."""

    changed = False
    for field_name, value in payload.items():
        if getattr(instance, field_name) != value:
            setattr(instance, field_name, value)
            changed = True
    return changed


def upsert_by_filters(
    session: Session,
    model: type,
    *,
    filters: list[Any],
    payload: dict[str, Any],
) -> tuple[Any, UpsertStatus]:
    """Create or update one parent row based on explicit identity filters."""

    existing = session.execute(select(model).where(and_(*filters))).scalar_one_or_none()
    if existing is None:
        instance = model(**payload)
        session.add(instance)
        session.flush()
        return instance, "inserted"

    changed = apply_payload_updates(existing, payload)
    return existing, "updated" if changed else "ignored"


def replace_child_rows(
    session: Session,
    child_model: type,
    *,
    parent_field: str,
    parent_id: Any,
    rows: list[dict[str, Any]],
) -> None:
    """Replace all child rows for one parent with the supplied projection."""

    session.query(child_model).filter(getattr(child_model, parent_field) == parent_id).delete()
    for row in rows:
        session.add(child_model(**{parent_field: parent_id, **row}))
