from __future__ import annotations

from .config import ObservabilityConfig, load_observability_config_from_env
from .langsmith_provider import LangSmithObservabilityProvider
from .noop import NoOpObservabilityProvider
from .provider import ObservabilityProvider


def build_observability_provider(
    config: ObservabilityConfig | None = None,
) -> ObservabilityProvider:
    resolved_config = config or load_observability_config_from_env()
    if not resolved_config.enabled or resolved_config.provider == "noop":
        return NoOpObservabilityProvider()
    if (
        resolved_config.provider == "langsmith"
        and resolved_config.langsmith is not None
    ):
        return LangSmithObservabilityProvider(resolved_config.langsmith)
    raise ValueError(
        f"Provider de observabilidade nao suportado: {resolved_config.provider}."
    )
