from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ossmk.core.models import ContributionEvent


class StorageBackend(ABC):
    @abstractmethod
    def ensure_schema(self) -> None:  # idempotent
        ...

    @abstractmethod
    def save_events(self, events: Iterable[ContributionEvent]) -> int:
        ...

    @abstractmethod
    def save_scores(self, scores: list[dict[str, object]]) -> int:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


def open_backend(dsn: str) -> StorageBackend:
    """Open a storage backend based on DSN.

    Examples:
    - postgresql://user:pass@host:5432/db
    - sqlite:///absolute/path/to/file.db
    - sqlite:///:memory:
    """
    if dsn.startswith("postgres://") or dsn.startswith("postgresql://"):
        from .postgres import PostgresBackend

        return PostgresBackend(dsn)
    if dsn.startswith("sqlite://"):
        from .sqlite import SQLiteStorage

        return SQLiteStorage(dsn)
    raise ValueError(f"Unsupported DSN: {dsn}")
