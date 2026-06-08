"""Configuracao compartilhada de paths e ambiente do runtime."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
ENV_FILE_PATH: Final[Path] = PROJECT_ROOT / ".env"
_ENV_LOADED = False
DEFAULT_DATABASE_URL = "sqlite:///database/transparencia.db"
DEFAULT_CLI_DATA_DIRECTORY: Final[Path] = PROJECT_ROOT / "data" / "xml"
DEFAULT_CHATBOT_SYSTEM_PROMPT_PATH: Final[Path] = (
    PROJECT_ROOT / "docs" / "agent-system-prompt.md"
)
DEFAULT_RAG_SOURCE_DIRECTORY: Final[Path] = PROJECT_ROOT / "data" / "rag"
DEFAULT_RAG_PERSIST_DIRECTORY: Final[Path] = (
    PROJECT_ROOT / "vector_store" / "knowledge_markdown"
)
DEFAULT_DOCKER_PORT = "8501"
DEFAULT_DOCKER_DATABASE_URL = "sqlite:////app/runtime/database/transparencia.db"
DEFAULT_DOCKER_RAG_PERSIST_DIRECTORY = "/app/runtime/vector_store/knowledge_markdown"
DEFAULT_AUTO_BOOTSTRAP_ON_START = "1"


@dataclass(frozen=True, slots=True)
class DockerRuntimeDefaults:
    port: str = DEFAULT_DOCKER_PORT
    database_url: str = DEFAULT_DOCKER_DATABASE_URL
    rag_persist_directory: str = DEFAULT_DOCKER_RAG_PERSIST_DIRECTORY
    auto_bootstrap_on_start: str = DEFAULT_AUTO_BOOTSTRAP_ON_START


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_env_file_path() -> Path:
    return ENV_FILE_PATH


def load_project_env() -> Path:
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(get_env_file_path(), override=False)
        _ENV_LOADED = True
    return get_env_file_path()


def get_env_value(name: str) -> str | None:
    load_project_env()
    return os.getenv(name)


def get_env_with_default(
    name: str,
    default: str,
    *,
    treat_blank_as_missing: bool = False,
) -> str:
    value = get_env_value(name)
    if value is None:
        return default
    if treat_blank_as_missing and not value.strip():
        return default
    return value


def read_required_env(name: str) -> str:
    value = get_env_value(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} deve ser informado no ambiente ou no .env.")
    return value.strip()


def resolve_project_path(value: str | Path | None, *, default: Path) -> Path:
    if value is None:
        candidate = default
    elif isinstance(value, Path):
        candidate = value.expanduser()
    else:
        cleaned = value.strip()
        candidate = Path(cleaned).expanduser() if cleaned else default

    if not candidate.is_absolute():
        candidate = get_project_root() / candidate
    return candidate.resolve()


def get_database_url() -> str:
    return get_env_with_default("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_cli_data_directory() -> Path:
    return DEFAULT_CLI_DATA_DIRECTORY


def get_chatbot_system_prompt_path() -> Path:
    return DEFAULT_CHATBOT_SYSTEM_PROMPT_PATH


def get_rag_source_directory() -> Path:
    return resolve_project_path(
        get_env_value("RAG_SOURCE_DIRECTORY"),
        default=DEFAULT_RAG_SOURCE_DIRECTORY,
    )


def get_rag_persist_directory() -> Path:
    return resolve_project_path(
        get_env_value("RAG_PERSIST_DIRECTORY"),
        default=DEFAULT_RAG_PERSIST_DIRECTORY,
    )


def get_docker_runtime_defaults() -> DockerRuntimeDefaults:
    return DockerRuntimeDefaults()


load_project_env()
