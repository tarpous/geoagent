"""Database settings and connection helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseSettings:
    dsn: str

    @classmethod
    def from_env(cls) -> DatabaseSettings:
        dsn = os.environ.get(
            "GEOAGENT_DATABASE_URL",
            "postgresql://geoagent:geoagent@127.0.0.1:5432/geoagent",
        )
        return cls(dsn=dsn)


def connect(dsn: str | None = None):
    """Return a psycopg connection with pgvector registered."""
    import psycopg
    from pgvector.psycopg import register_vector

    settings = DatabaseSettings.from_env() if dsn is None else DatabaseSettings(dsn=dsn)
    conn = psycopg.connect(settings.dsn)
    register_vector(conn)
    return conn
