from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from .config import LangSmithObservabilityConfig
from .events import build_error_payload
from .provider import BaseObservabilityProvider
from .sanitization import sanitize_mapping
from .types import ObservationPayload, ObservationRunType


class _LangSmithSpan:
    def __init__(self, run: Any) -> None:
        self._run = run
        self._outputs: ObservationPayload = {}
        self._metadata: ObservationPayload = {}
        self._error: BaseException | None = None

    def set_outputs(self, outputs: Mapping[str, Any] | None = None) -> None:
        if not outputs:
            return
        self._outputs.update(sanitize_mapping(outputs))

    def set_metadata(self, metadata: Mapping[str, Any] | None = None) -> None:
        if not metadata:
            return
        self._metadata.update(sanitize_mapping(metadata))

    def record_error(self, error: BaseException) -> None:
        self._error = error
        self._metadata.update(build_error_payload(error))

    def finalize(self) -> None:
        error_message = None
        if self._error is not None:
            error_message = (
                f"{self._error.__class__.__name__}: {str(self._error).strip()}"
            ).strip()
        self._run.end(
            outputs=self._outputs or None,
            error=error_message,
            metadata=self._metadata or None,
        )


class LangSmithObservabilityProvider(BaseObservabilityProvider):
    name = "langsmith"

    def __init__(self, config: LangSmithObservabilityConfig) -> None:
        from langsmith.client import Client

        client_kwargs = {"api_key": config.api_key}
        if config.endpoint:
            client_kwargs["api_url"] = config.endpoint
        self._client = Client(**client_kwargs)
        self._project_name = config.project

    @contextmanager
    def span(
        self,
        name: str,
        *,
        run_type: ObservationRunType = "chain",
        inputs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        tags: Sequence[str] | None = None,
    ) -> Iterator[_LangSmithSpan]:
        from langsmith.run_helpers import trace, tracing_context

        sanitized_inputs = sanitize_mapping(inputs)
        sanitized_metadata = sanitize_mapping(metadata)
        sanitized_tags = [str(tag) for tag in (tags or ())]

        with tracing_context(
            enabled=True,
            client=self._client,
            project_name=self._project_name,
        ):
            with trace(
                name,
                run_type=run_type,
                inputs=sanitized_inputs or None,
                metadata=sanitized_metadata or None,
                tags=sanitized_tags or None,
                project_name=self._project_name,
                client=self._client,
            ) as run:
                span = _LangSmithSpan(run)
                try:
                    yield span
                except Exception as exc:
                    span.record_error(exc)
                    raise
                finally:
                    span.finalize()
