"""Standalone database migration runner for init containers and Kubernetes Jobs.
Performs exponential backoff connectivity check and applies Alembic migrations to head.
"""

import logging
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

# Add parent directory to sys.path so config/models can be imported
app_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(app_dir))

from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("taskapi.migrate")


def wait_for_database(max_retries: int = 30, delay_seconds: float = 2.0) -> bool:
    """Blocks until database is accepting connections or retries are exhausted."""
    logger.info("Verifying database connectivity at %s...", settings.database_url.split("@")[-1])
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    )

    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully on attempt %d.", attempt)
            return True
        except Exception as exc:
            logger.warning(
                "Database connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                delay_seconds,
            )
            time.sleep(delay_seconds)
            delay_seconds = min(10.0, delay_seconds * 1.2)

    logger.error("Failed to connect to database after %d attempts.", max_retries)
    return False


def run_migrations() -> None:
    """Applies all pending Alembic migrations up to head."""
    ini_path = app_dir.parent / "alembic.ini"
    if not ini_path.exists():
        ini_path = app_dir / "alembic.ini"

    logger.info("Loading Alembic configuration from %s", ini_path)
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(app_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    logger.info("Executing Alembic upgrade head...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations completed successfully.")


def main():
    if not wait_for_database():
        sys.exit(1)
    try:
        run_migrations()
    except Exception as exc:
        logger.exception("Migration execution failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
