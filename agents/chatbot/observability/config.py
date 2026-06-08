from __future__ import annotations

from dataclasses import dataclass
import os

SUPPORTED_OBSERVABILITY_PROVIDERS = ("noop", "langsmith")
_NOOP_PROVIDER_ALIASES = {"", "none", "noop"}


@dataclass(frozen=True, slots=True)
class LangSmithObservabilityConfig:
    api_key: str
    project: str
    endpoint: str | None = None


@dataclass(frozen=True, slots=True)
class ObservabilityConfig:
    enabled: bool
    provider: str
    langsmith: LangSmithObservabilityConfig | None = None


def load_observability_config_from_env() -> ObservabilityConfig:
    enabled = _parse_bool_env("OBSERVABILITY_ENABLED")
    provider = _normalize_provider(os.getenv("OBSERVABILITY_PROVIDER"))

    if not enabled or provider in _NOOP_PROVIDER_ALIASES:
        return ObservabilityConfig(enabled=False, provider="noop")

    if provider != "langsmith":
        supported = ", ".join(SUPPORTED_OBSERVABILITY_PROVIDERS)
        raise ValueError(
            f"Provider de observabilidade nao suportado: {provider}. "
            f"Providers suportados nesta fase: {supported}."
        )

    return ObservabilityConfig(
        enabled=True,
        provider="langsmith",
        langsmith=LangSmithObservabilityConfig(
            api_key=_read_required_provider_env("LANGSMITH_API_KEY"),
            project=_read_required_provider_env("LANGSMITH_PROJECT"),
            endpoint=_read_optional_env("LANGSMITH_ENDPOINT"),
        ),
    )


def _parse_bool_env(var_name: str) -> bool:
    raw_value = _read_optional_env(var_name)
    if raw_value is None:
        return False
    return raw_value.lower() in {"1", "true", "yes", "on"}


def _normalize_provider(raw_value: str | None) -> str:
    if raw_value is None:
        return ""
    return raw_value.strip().lower()


def _read_required_provider_env(var_name: str) -> str:
    value = _read_optional_env(var_name)
    if value is None:
        raise ValueError(
            f"{var_name} deve ser informado quando OBSERVABILITY_PROVIDER=langsmith."
        )
    return value


def _read_optional_env(var_name: str) -> str | None:
    value = os.getenv(var_name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
