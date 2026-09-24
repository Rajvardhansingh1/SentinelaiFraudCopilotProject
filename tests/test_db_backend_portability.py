"""D-053: DATABASE_URL must work against both SQLite (default, tests) and
Postgres/Supabase (production) without code changes beyond the URL itself."""

from proxy.db.session import _connect_args, _with_explicit_driver


def test_sqlite_url_gets_check_same_thread_kwarg():
    assert _connect_args("sqlite:///./data/logs.db") == {"check_same_thread": False}
    assert _connect_args("sqlite:///:memory:") == {"check_same_thread": False}


def test_postgres_url_gets_no_sqlite_only_kwarg():
    """Regression: check_same_thread is a pysqlite-only kwarg. psycopg2 raises
    TypeError if it's passed — this must be empty for any non-sqlite URL."""
    assert _connect_args("postgresql://user:pass@host:5432/postgres") == {}
    assert _connect_args("postgresql+psycopg2://user:pass@host:5432/postgres") == {}


def test_bare_postgres_url_gets_psycopg2_driver_pinned():
    """Regression: a bare "postgresql://" URL (Supabase's documented format)
    must not be left for SQLAlchemy to pick a default DBAPI — that default
    isn't guaranteed across SQLAlchemy versions and this project only
    installs psycopg2-binary, not psycopg (v3). An unpinned requirements.txt
    bump silently changed that default in production and crashed the app at
    startup with ModuleNotFoundError: No module named 'psycopg'."""
    assert _with_explicit_driver("postgresql://user:pass@host:5432/postgres") == (
        "postgresql+psycopg2://user:pass@host:5432/postgres"
    )


def test_already_explicit_driver_url_is_unchanged():
    assert _with_explicit_driver("postgresql+psycopg2://user:pass@host:5432/postgres") == (
        "postgresql+psycopg2://user:pass@host:5432/postgres"
    )


def test_sqlite_url_is_unchanged():
    assert _with_explicit_driver("sqlite:///:memory:") == "sqlite:///:memory:"
