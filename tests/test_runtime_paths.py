from pathlib import Path

from database.session import _ensure_sqlite_storage_directory


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
