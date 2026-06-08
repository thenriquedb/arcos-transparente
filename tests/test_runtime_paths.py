from __future__ import annotations

from contextlib import nullcontext
import importlib
from pathlib import Path
import sys

from alembic import context as alembic_context

import agents.chatbot.agent as chatbot_agent
from database.session import _ensure_sqlite_storage_directory
from shared.runtime_config import (
    DEFAULT_DATABASE_URL,
    get_chatbot_system_prompt_path,
    get_cli_data_directory,
    get_database_url,
    get_docker_runtime_defaults,
    get_env_file_path,
    get_project_root,
    get_rag_persist_directory,
    get_rag_source_directory,
)


def test_ensure_sqlite_storage_directory_creates_parent_for_file_database(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "runtime" / "database" / "transparencia.db"

    _ensure_sqlite_storage_directory(f"sqlite:///{db_path}")

    assert db_path.parent.exists()


def test_ensure_sqlite_storage_directory_ignores_memory_database(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "nao-deve-existir"

    _ensure_sqlite_storage_directory("sqlite:///:memory:")

    assert not marker.exists()


def test_runtime_config_expoe_paths_padrao_do_projeto() -> None:
    project_root = get_project_root()

    assert get_env_file_path() == project_root / ".env"
    assert get_cli_data_directory() == project_root / "data" / "xml"
    assert get_chatbot_system_prompt_path() == (
        project_root / "docs" / "agent-system-prompt.md"
    )


def test_runtime_config_resolve_paths_do_rag_com_env(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RAG_SOURCE_DIRECTORY", "dados/rag-custom")
    monkeypatch.setenv("RAG_PERSIST_DIRECTORY", str(tmp_path / "vector-store"))

    assert (
        get_rag_source_directory()
        == (get_project_root() / "dados" / "rag-custom").resolve()
    )
    assert get_rag_persist_directory() == (tmp_path / "vector-store").resolve()


def test_runtime_config_expoe_database_url_e_defaults_do_docker(
    monkeypatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_database_url() == DEFAULT_DATABASE_URL

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert get_database_url() == "sqlite:///:memory:"

    docker_defaults = get_docker_runtime_defaults()
    assert docker_defaults.port == "8501"
    assert docker_defaults.database_url.endswith(
        "/app/runtime/database/transparencia.db"
    )
    assert docker_defaults.rag_persist_directory.endswith(
        "/app/runtime/vector_store/knowledge_markdown"
    )
    assert docker_defaults.auto_bootstrap_on_start == "1"


def test_chatbot_bootstrap_import_usa_runtime_config(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    reloaded = importlib.reload(chatbot_agent)

    assert reloaded.SYSTEM_PROMPT_PATH == get_chatbot_system_prompt_path()
    assert reloaded.obter_configuracao_llm()["model_name"] == "gpt-4.1-mini"


def test_migration_env_smoke_import_usa_runtime_database_url(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class FakeAlembicConfig:
        def __init__(self) -> None:
            self.config_file_name = None
            self.config_ini_section = "alembic"
            self._options: dict[str, str] = {}

        def set_main_option(self, key: str, value: str) -> None:
            self._options[key] = value

        def get_main_option(self, key: str) -> str:
            return self._options[key]

        def get_section(self, _section: str, default):
            return default

    database_url = f"sqlite:///{tmp_path / 'migration-smoke.db'}"
    fake_config = FakeAlembicConfig()
    captured: dict[str, object] = {}

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setattr(alembic_context, "config", fake_config, raising=False)
    monkeypatch.setattr(
        alembic_context,
        "is_offline_mode",
        lambda: True,
        raising=False,
    )
    monkeypatch.setattr(
        alembic_context,
        "configure",
        lambda **kwargs: captured.update(kwargs),
        raising=False,
    )
    monkeypatch.setattr(
        alembic_context,
        "begin_transaction",
        lambda: nullcontext(),
        raising=False,
    )
    monkeypatch.setattr(
        alembic_context,
        "run_migrations",
        lambda: captured.setdefault("ran_migrations", True),
        raising=False,
    )

    sys.modules.pop("database.migrations.env", None)
    module = importlib.import_module("database.migrations.env")

    assert fake_config.get_main_option("sqlalchemy.url") == database_url
    assert captured["url"] == database_url
    assert captured["target_metadata"] is module.target_metadata
