from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from proxy.config import settings
from proxy.db.models import Base


def _connect_args(database_url: str) -> dict:
    # check_same_thread is a SQLite-only pysqlite kwarg — passing it to a
    # Postgres/Supabase URL (psycopg2) raises a TypeError at connect time.
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


_is_memory = ":memory:" in settings.database_url
_engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
    poolclass=StaticPool if _is_memory else None,
)
SessionLocal = sessionmaker(bind=_engine)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    return SessionLocal()
