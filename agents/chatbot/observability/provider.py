"""Contrato (protocolo) que todo provider de observabilidade implementa."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any, Protocol

from .types import ObservationPayload, ObservationRunType


class ObservabilitySpan(Protocol):
    def set_outputs(self, outputs: Mapping[str, Any] | None = None) -> None:
        """Atualiza o payload de saída do span atual."""

    def set_metadata(self, metadata: Mapping[str, Any] | None = None) -> None:
        """Atualiza o metadata do span atual."""

    def record_error(self, error: BaseException) -> None:
        """Registra o erro associado ao span atual."""


class ObservabilityProvider(Protocol):
    name: str

    @contextmanager
    def span(
        self,
        name: str,
        *,
        run_type: ObservationRunType = "chain",
        inputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        tags: Sequence[str] | None = None,
    ) -> Iterator[ObservabilitySpan]:
        """Abre um span observável dentro do provider ativo."""

    def emit_event(
        self,
        name: str,
        *,
        run_type: ObservationRunType = "chain",
        inputs: Mapping[str, Any] | None = None,
        outputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:
        """Emite um evento pontual usando o contrato compartilhado."""


class BaseObservabilityProvider:
    name = "noop"

    def emit_event(
        self,
        name: str,
        *,
        run_type: ObservationRunType = "chain",
        inputs: Mapping[str, Any] | None = None,
        outputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:
        with self.span(
            name,
            run_type=run_type,
            inputs=inputs,
            metadata=metadata,
            tags=tags,
        ) as span:
            span.set_outputs(outputs)


class NoOpSpan:
    def set_outputs(self, outputs: Mapping[str, Any] | None = None) -> None:
        _ = outputs

    def set_metadata(self, metadata: Mapping[str, Any] | None = None) -> None:
        _ = metadata

    def record_error(self, error: BaseException) -> None:
        _ = error
