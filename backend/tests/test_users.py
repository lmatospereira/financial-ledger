"""GET/POST/PUT/DELETE /api/users (admin-only), GET /api/auth/me,
PUT /api/users/me/password.
"""
from tests.conftest import TEST_PASSWORD, TEST_USERNAME


def make_regular_user(db_session):
    """A second, non-admin user, created directly (not via the admin-only
    /api/users endpoint) so tests that check 403-for-non-admin don't depend
    on the endpoint under test.
    """
    from app import auth, crud

    return crud.create_user(
        db_session, username="regular", password_hash=auth.hash_password("regularpass123")
    )


def login(client, username, password):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- GET /api/auth/me ----------
def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == TEST_USERNAME
    assert body["is_admin"] is True
    assert "id" in body


def test_me_requires_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


# ---------- GET/POST /api/users ----------
def test_list_users_admin_only(client, auth_headers, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.get("/api/users", headers=headers)
    assert response.status_code == 403


def test_list_users_as_admin(client, auth_headers, db_session):
    make_regular_user(db_session)
    response = client.get("/api/users", headers=auth_headers)
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert usernames == {TEST_USERNAME, "regular"}


def test_create_user_as_admin(client, auth_headers):
    response = client.post(
        "/api/users",
        json={"username": "newuser", "password": "newuserpass123", "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newuser"
    assert body["is_admin"] is False
    assert "id" in body
    assert "password" not in body


def test_create_user_duplicate_username(client, auth_headers):
    client.post(
        "/api/users",
        json={"username": "dup", "password": "duppass123", "is_admin": False},
        headers=auth_headers,
    )
    response = client.post(
        "/api/users",
        json={"username": "dup", "password": "otherpass123", "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_user_non_admin_forbidden(client, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.post(
        "/api/users",
        json={"username": "sneaky", "password": "sneakypass123", "is_admin": True},
        headers=headers,
    )
    assert response.status_code == 403


def test_create_user_requires_auth(client):
    response = client.post(
        "/api/users", json={"username": "x", "password": "xpassword123", "is_admin": False}
    )
    assert response.status_code == 401


# ---------- PUT /api/users/{id} ----------
def test_update_user_as_admin(client, auth_headers):
    created = client.post(
        "/api/users",
        json={"username": "editme", "password": "editmepass123", "is_admin": False},
        headers=auth_headers,
    ).json()
    response = client.put(
        f"/api/users/{created['id']}",
        json={"username": "edited", "is_admin": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "edited"
    assert body["is_admin"] is True


def test_update_user_not_found(client, auth_headers):
    response = client.put(
        "/api/users/999", json={"username": "x", "is_admin": False}, headers=auth_headers
    )
    assert response.status_code == 404


def test_update_user_non_admin_forbidden(client, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.put(
        "/api/users/1", json={"username": "x", "is_admin": False}, headers=headers
    )
    assert response.status_code == 403


# ---------- DELETE /api/users/{id} ----------
def test_delete_user_as_admin(client, auth_headers):
    created = client.post(
        "/api/users",
        json={"username": "deleteme", "password": "deletemepass123", "is_admin": False},
        headers=auth_headers,
    ).json()
    response = client.delete(f"/api/users/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    listing = client.get("/api/users", headers=auth_headers).json()
    assert created["id"] not in [u["id"] for u in listing]


def test_delete_user_not_found(client, auth_headers):
    response = client.delete("/api/users/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_user_non_admin_forbidden(client, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.delete("/api/users/1", headers=headers)
    assert response.status_code == 403


def test_delete_user_cascades_accounts_and_transactions(client, auth_headers):
    created = client.post(
        "/api/users",
        json={"username": "cascadeuser", "password": "cascadepass123", "is_admin": False},
        headers=auth_headers,
    ).json()
    headers = login(client, "cascadeuser", "cascadepass123")
    account = client.post(
        "/api/accounts",
        json={"name": "Their Account", "type": "checking", "color": "#111111"},
        headers=headers,
    ).json()
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Something",
            "amount": 10.0,
            "type": "income",
            "category_id": None,
            "account_id": account["id"],
        },
        headers=headers,
    )

    response = client.delete(f"/api/users/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    # The deleted user's token is now for a nonexistent user -- further
    # authenticated calls with it must fail.
    response = client.get("/api/accounts", headers=headers)
    assert response.status_code == 401


# ---------- PUT /api/users/me/password ----------
def test_change_password_success(client, auth_headers):
    response = client.put(
        "/api/users/me/password",
        json={"current_password": TEST_PASSWORD, "new_password": "brandnewpass123"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Old password no longer works, new one does.
    old_login = client.post(
        "/api/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login", json={"username": TEST_USERNAME, "password": "brandnewpass123"}
    )
    assert new_login.status_code == 200


def test_change_password_wrong_current(client, auth_headers):
    response = client.put(
        "/api/users/me/password",
        json={"current_password": "wrongpassword", "new_password": "brandnewpass123"},
        headers=auth_headers,
    )
    assert response.status_code == 401


def test_change_password_requires_auth(client):
    response = client.put(
        "/api/users/me/password",
        json={"current_password": "a", "new_password": "b"},
    )
    assert response.status_code == 401


def test_change_password_any_authenticated_user(client, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.put(
        "/api/users/me/password",
        json={"current_password": "regularpass123", "new_password": "newregularpass123"},
        headers=headers,
    )
    assert response.status_code == 200
