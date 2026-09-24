from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from proxy.config import settings
from proxy.db.models import Base


def _connect_args(database_url: str) -> dict:
    # check_same_thread is a SQLite-only pysqlite kwarg — passing it to a
    # Postgres/Supabase URL (psycopg2) raises a TypeError at connect time.
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


def _with_explicit_driver(database_url: str) -> str:
    # A bare "postgresql://" URL (e.g. Supabase's documented connection
    # string format) leaves SQLAlchemy to pick a default DBAPI, and that
    # default isn't guaranteed to be psycopg2 across SQLAlchemy versions —
    # requirements.txt is unpinned, so a routine dependency bump can silently
    # resolve it to psycopg (v3), which this project doesn't install,
    # crashing the app at startup with ModuleNotFoundError. Pin the driver
    # explicitly so it matches the psycopg2-binary dependency this project
    # actually ships (D-053), independent of SQLAlchemy's own default.
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + database_url[len("postgresql://"):]
    return database_url


_is_memory = ":memory:" in settings.database_url
_engine = create_engine(
    _with_explicit_driver(settings.database_url),
    connect_args=_connect_args(settings.database_url),
    poolclass=StaticPool if _is_memory else None,
)
SessionLocal = sessionmaker(bind=_engine)


# Phase 2 (D-055): tables that gained a nullable project_id column after
# already shipping. `create_all()` only creates missing TABLES, never adds
# columns to ones that already exist — so an already-deployed DB needs this
# explicit, additive-only migration. Nullable + no default touches zero
# existing rows (spec_V3.md §61/§62: preserve existing data, never a
# destructive schema change).
_TABLES_NEEDING_PROJECT_ID = [
    "call_logs",
    "findings",
    "test_run_results",
    "agent_action_logs",
    "security_events",
    "baselines",
]

# Phase 3 (D-056): additive columns added to already-existing tables after
# they first shipped. Same pattern as _TABLES_NEEDING_PROJECT_ID above —
# nullable/defaulted, never a destructive schema change.
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("test_run_results", "execution_source", "VARCHAR DEFAULT 'dashboard'"),
    ("projects", "repo_url", "VARCHAR"),
    ("projects", "description", "VARCHAR"),
]


def _migrate_add_project_id_columns() -> None:
    inspector = inspect(_engine)
    existing_tables = set(inspector.get_table_names())
    with _engine.begin() as conn:
        for table in _TABLES_NEEDING_PROJECT_ID:
            if table not in existing_tables:
                continue  # create_all() will create it with the column already present
            columns = {c["name"] for c in inspector.get_columns(table)}
            if "project_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN project_id INTEGER"))
        for table, column, ddl_type in _ADDITIVE_COLUMNS:
            if table not in existing_tables:
                continue
            columns = {c["name"] for c in inspector.get_columns(table)}
            if column not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def init_db() -> None:
    Base.metadata.create_all(_engine)
    _migrate_add_project_id_columns()


def get_session() -> Session:
    return SessionLocal()
