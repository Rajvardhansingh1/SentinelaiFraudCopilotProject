"""D-053: DATABASE_URL must work against both SQLite (default, tests) and
Postgres/Supabase (production) without code changes beyond the URL itself."""

from proxy.db.session import _connect_args


def test_sqlite_url_gets_check_same_thread_kwarg():
    assert _connect_args("sqlite:///./data/logs.db") == {"check_same_thread": False}
    assert _connect_args("sqlite:///:memory:") == {"check_same_thread": False}


def test_postgres_url_gets_no_sqlite_only_kwarg():
    """Regression: check_same_thread is a pysqlite-only kwarg. psycopg2 raises
    TypeError if it's passed — this must be empty for any non-sqlite URL."""
    assert _connect_args("postgresql://user:pass@host:5432/postgres") == {}
    assert _connect_args("postgresql+psycopg2://user:pass@host:5432/postgres") == {}
