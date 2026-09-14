import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force a fresh in-memory DB and disabled cache before any app module loads,
# so the test suite never touches a real Postgres/Redis instance.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CACHE_ENABLED"] = "false"

import pytest  # noqa: E402
from database import Base, get_db  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
