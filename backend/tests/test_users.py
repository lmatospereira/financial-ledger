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
        db_session,
        username="regular",
        name="Regular User",
        password_hash=auth.hash_password("regularpass123"),
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
        json={"username": "newuser", "name": "New User", "password": "newuserpass123", "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newuser"
    assert body["name"] == "New User"
    assert body["is_admin"] is False
    assert "id" in body
    assert "password" not in body


def test_create_user_normalizes_username_to_lowercase(client, auth_headers):
    response = client.post(
        "/api/users",
        json={"username": "  MixedCase  ", "name": "Mixed", "password": "mixedpass123", "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["username"] == "mixedcase"


def test_login_is_case_insensitive(client, auth_headers):
    client.post(
        "/api/users",
        json={"username": "caseuser", "name": "Case User", "password": "casepass123", "is_admin": False},
        headers=auth_headers,
    )
    for attempt in ("CASEUSER", "CaseUser", "caseuser"):
        response = client.post(
            "/api/auth/login", json={"username": attempt, "password": "casepass123"}
        )
        assert response.status_code == 200, f"login failed for {attempt!r}: {response.text}"


def test_create_user_duplicate_username(client, auth_headers):
    client.post(
        "/api/users",
        json={"username": "dup", "name": "Dup", "password": "duppass123", "is_admin": False},
        headers=auth_headers,
    )
    response = client.post(
        "/api/users",
        json={"username": "dup", "name": "Dup 2", "password": "otherpass123", "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_user_non_admin_forbidden(client, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.post(
        "/api/users",
        json={"username": "sneaky", "name": "Sneaky", "password": "sneakypass123", "is_admin": True},
        headers=headers,
    )
    assert response.status_code == 403


def test_create_user_requires_auth(client):
    response = client.post(
        "/api/users",
        json={"username": "x", "name": "X", "password": "xpassword123", "is_admin": False},
    )
    assert response.status_code == 401


# ---------- PUT /api/users/{id} ----------
def test_update_user_as_admin(client, auth_headers):
    created = client.post(
        "/api/users",
        json={"username": "editme", "name": "Edit Me", "password": "editmepass123", "is_admin": False},
        headers=auth_headers,
    ).json()
    response = client.put(
        f"/api/users/{created['id']}",
        json={"username": "edited", "name": "Edited", "is_admin": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "edited"
    assert body["name"] == "Edited"
    assert body["is_admin"] is True


def test_update_user_not_found(client, auth_headers):
    response = client.put(
        "/api/users/999",
        json={"username": "x", "name": "X", "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_user_non_admin_forbidden(client, db_session):
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")
    response = client.put(
        "/api/users/1", json={"username": "x", "name": "X", "is_admin": False}, headers=headers
    )
    assert response.status_code == 403


# ---------- DELETE /api/users/{id} ----------
def test_delete_user_as_admin(client, auth_headers):
    created = client.post(
        "/api/users",
        json={"username": "deleteme", "name": "Delete Me", "password": "deletemepass123", "is_admin": False},
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
        json={"username": "cascadeuser", "name": "Cascade User", "password": "cascadepass123", "is_admin": False},
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


# ---------- POST /api/users/{user_id}/reset-password ----------
def test_reset_password_admin_only(client, auth_headers, db_session):
    # Create a target user and a non-admin user
    target = client.post(
        "/api/users",
        json={"username": "target", "name": "Target", "password": "targetpass123", "is_admin": False},
        headers=auth_headers,
    ).json()
    make_regular_user(db_session)
    headers = login(client, "regular", "regularpass123")

    # Non-admin cannot reset another user's password
    response = client.post(
        f"/api/users/{target['id']}/reset-password",
        json={"new_password": "newpass123"},
        headers=headers,
    )
    assert response.status_code == 403


def test_reset_password_as_admin(client, auth_headers):
    # Create a target user
    target = client.post(
        "/api/users",
        json={"username": "target", "name": "Target", "password": "targetpass123", "is_admin": False},
        headers=auth_headers,
    ).json()

    # Admin can reset the password
    response = client.post(
        f"/api/users/{target['id']}/reset-password",
        json={"new_password": "brandnewpass123"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target["id"]

    # Verify the user can log in with the new password
    login_response = client.post(
        "/api/auth/login",
        json={"username": "target", "password": "brandnewpass123"},
    )
    assert login_response.status_code == 200

    # Verify the old password no longer works
    old_login = client.post(
        "/api/auth/login",
        json={"username": "target", "password": "targetpass123"},
    )
    assert old_login.status_code == 401


def test_reset_password_user_not_found(client, auth_headers):
    response = client.post(
        "/api/users/999/reset-password",
        json={"new_password": "newpass123"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_reset_password_too_short(client, auth_headers):
    # Create a target user
    target = client.post(
        "/api/users",
        json={"username": "target", "name": "Target", "password": "targetpass123", "is_admin": False},
        headers=auth_headers,
    ).json()

    # Attempt to reset with password < 8 chars should fail with 422
    response = client.post(
        f"/api/users/{target['id']}/reset-password",
        json={"new_password": "short"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_reset_password_requires_auth(client):
    response = client.post(
        "/api/users/1/reset-password",
        json={"new_password": "newpass123"},
    )
    assert response.status_code == 401


# ---------- PUT /api/users/me/dashboard-preferences ----------
def test_update_dashboard_preferences_sets_hidden_widgets(client, auth_headers):
    response = client.put(
        "/api/users/me/dashboard-preferences",
        json={"hidden_widgets": ["balance", "alerts"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_hidden_widgets"] == ["balance", "alerts"]


def test_update_dashboard_preferences_empty_list(client, auth_headers):
    response = client.put(
        "/api/users/me/dashboard-preferences",
        json={"hidden_widgets": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_hidden_widgets"] == []


def test_update_dashboard_preferences_persists(client, auth_headers, db_session):
    # Update preferences
    client.put(
        "/api/users/me/dashboard-preferences",
        json={"hidden_widgets": ["balance"]},
        headers=auth_headers,
    )

    # Verify it persists in a subsequent GET /api/auth/me
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_hidden_widgets"] == ["balance"]


def test_update_dashboard_preferences_requires_auth(client):
    response = client.put(
        "/api/users/me/dashboard-preferences",
        json={"hidden_widgets": ["balance"]},
    )
    assert response.status_code == 401


def test_user_without_preferences_gets_empty_list(client, auth_headers):
    # A user created without setting preferences should get an empty list, not None
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_hidden_widgets"] == []
    assert body["dashboard_hidden_widgets"] is not None
