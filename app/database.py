"""SQLAlchemy engine/session setup. Works against SQLite (local/test) or
Postgres (Kubernetes) depending on DATABASE_URL with zero code changes.
"""

from config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if not is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
            "pool_recycle": settings.db_pool_recycle,
        }
    )

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and guarantees cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    """Verifies that the database connection is alive and responsive."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_db() -> None:
    """Create tables if they don't exist. Safe fallback for local/test runs."""
    Base.metadata.create_all(bind=engine)
