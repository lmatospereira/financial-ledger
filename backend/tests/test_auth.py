from tests.conftest import TEST_PASSWORD, TEST_USERNAME


def test_login_success(client, seed_admin):
    response = client.post(
        "/api/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, seed_admin):
    response = client.post(
        "/api/auth/login", json={"username": TEST_USERNAME, "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert response.status_code == 401


def test_health_no_auth_required(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_without_token(client):
    response = client.get("/api/categories")
    assert response.status_code == 401


def test_protected_route_with_invalid_token(client):
    response = client.get(
        "/api/categories", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_protected_route_with_valid_token(client, auth_headers):
    response = client.get("/api/categories", headers=auth_headers)
    assert response.status_code == 200
