"""Isolated test DB fixture: a fresh in-memory SQLite DB per test, with the
FastAPI app's get_db dependency overridden to use it. Also provides a
pre-seeded admin user and a client authenticated as that user.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, crud
from app.database import Base, get_db
from app.main import app

TEST_USERNAME = "admin"
TEST_PASSWORD = "adminpass123"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Note: intentionally not using `with TestClient(app)` here, which would
    # run the app's lifespan (create_all/seed against the *real* on-disk
    # engine) — tests must stay fully isolated in the in-memory db_session.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_admin(db_session):
    return crud.create_user(
        db_session,
        username=TEST_USERNAME,
        password_hash=auth.hash_password(TEST_PASSWORD),
        is_admin=True,
    )


@pytest.fixture()
def auth_headers(client, seed_admin):
    response = client.post(
        "/api/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def default_account(client, auth_headers):
    """Every existing transaction test now needs an account_id; this fixture
    gives them a ready-made one owned by the default (admin) test user.
    """
    response = client.post(
        "/api/accounts",
        json={"name": "Main Checking", "type": "checking", "color": "#123456"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
