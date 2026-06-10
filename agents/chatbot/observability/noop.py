"""Provider nulo usado quando a observabilidade esta desligada."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from .provider import BaseObservabilityProvider, NoOpSpan
from .types import ObservationRunType


class NoOpObservabilityProvider(BaseObservabilityProvider):
    name = "noop"

    @contextmanager
    def span(
        self,
        name: str,
        *,
        run_type: ObservationRunType = "chain",
        inputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        tags: Sequence[str] | None = None,
    ) -> Iterator[NoOpSpan]:
        _ = (name, run_type, inputs, metadata, tags)
        yield NoOpSpan()
