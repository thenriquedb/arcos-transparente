"""Propagacao de contexto (request/session) para eventos de observabilidade."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

from .noop import NoOpObservabilityProvider
from .provider import ObservabilityProvider

_DEFAULT_PROVIDER = NoOpObservabilityProvider()
_CURRENT_PROVIDER: ContextVar[ObservabilityProvider] = ContextVar(
    "chatbot_observability_provider",
    default=_DEFAULT_PROVIDER,
)


def get_current_observability_provider() -> ObservabilityProvider:
    return _CURRENT_PROVIDER.get()


@contextmanager
def use_observability_provider(
    provider: ObservabilityProvider | None,
) -> Iterator[ObservabilityProvider]:
    active_provider = provider or _DEFAULT_PROVIDER
    token: Token[ObservabilityProvider] = _CURRENT_PROVIDER.set(active_provider)
    try:
        yield active_provider
    finally:
        _CURRENT_PROVIDER.reset(token)
