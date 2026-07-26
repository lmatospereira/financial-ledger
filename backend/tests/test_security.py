"""Tests for security features: rate limiting and password strength validation."""
from tests.conftest import TEST_PASSWORD, TEST_USERNAME


# ---------- Rate Limiting Tests ----------


def test_login_rate_limit_allows_5_attempts_per_minute(client, seed_admin):
    """Verify that login allows up to 5 failed attempts per minute."""
    for i in range(5):
        response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": "wrongpassword"},
        )
        assert response.status_code == 401, f"Attempt {i+1} should return 401"


def test_login_rate_limit_blocks_6th_attempt(client, seed_admin):
    """Verify that the 6th login attempt within a minute returns 429."""
    # Make 5 failed attempts (within limit)
    for i in range(5):
        response = client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": "wrongpassword"},
        )
        assert response.status_code == 401, f"Attempt {i+1} should return 401"

    # 6th attempt should hit rate limit
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": "wrongpassword"},
    )
    assert response.status_code == 429, f"6th attempt should return 429, got {response.status_code}"
    assert "detail" in response.json()


def test_login_rate_limit_response_format(client, seed_admin):
    """Verify rate limit error response follows the API's error shape."""
    # Make 5 attempts
    for _ in range(5):
        client.post(
            "/api/auth/login",
            json={"username": TEST_USERNAME, "password": "wrongpassword"},
        )

    # 6th attempt
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": "wrongpassword"},
    )
    assert response.status_code == 429
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body
    assert isinstance(body["detail"], str)


def test_password_change_rate_limit_blocks_after_5_attempts(client, auth_headers, db_session):
    """Verify that password change endpoint is rate-limited to 5/minute."""
    # Make 5 password change requests (all will fail due to wrong current password)
    for i in range(5):
        response = client.put(
            "/api/users/me/password",
            json={"current_password": "wrong", "new_password": "brandnewpass12345"},
            headers=auth_headers,
        )
        assert response.status_code == 401, f"Attempt {i+1} should return 401"

    # 6th attempt should hit rate limit
    response = client.put(
        "/api/users/me/password",
        json={"current_password": "wrong", "new_password": "brandnewpass12345"},
        headers=auth_headers,
    )
    assert response.status_code == 429


def test_create_user_rate_limit_allows_10_attempts(client, auth_headers):
    """Verify that create user endpoint allows up to 10 attempts per minute."""
    # Create 10 users successfully
    for i in range(10):
        response = client.post(
            "/api/users",
            json={
                "username": f"user{i}",
                "name": f"User {i}",
                "password": f"password{i}12345",
                "is_admin": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, f"User creation attempt {i+1} should succeed"


def test_create_user_rate_limit_blocks_11th_attempt(client, auth_headers):
    """Verify that the 11th create user attempt within a minute returns 429."""
    # Create 10 users successfully
    for i in range(10):
        response = client.post(
            "/api/users",
            json={
                "username": f"user{i}",
                "name": f"User {i}",
                "password": f"password{i}12345",
                "is_admin": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    # 11th attempt should hit rate limit
    response = client.post(
        "/api/users",
        json={
            "username": "user11",
            "name": "User 11",
            "password": "password11456789",
            "is_admin": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 429


# ---------- Password Strength Validation Tests ----------


def test_create_user_with_7_char_password_fails(client, auth_headers):
    """Password with 7 characters should be rejected at API level (< 8 min)."""
    response = client.post(
        "/api/users",
        json={
            "username": "shortpass",
            "name": "Short Pass",
            "password": "1234567",  # 7 characters
            "is_admin": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422, "Should fail validation"
    body = response.json()
    assert "detail" in body


def test_create_user_with_8_char_password_succeeds(client, auth_headers):
    """Password with exactly 8 characters should be accepted."""
    response = client.post(
        "/api/users",
        json={
            "username": "okpass",
            "name": "Ok Pass",
            "password": "12345678",  # 8 characters
            "is_admin": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, f"Should succeed: {response.text}"
    body = response.json()
    assert body["username"] == "okpass"


def test_create_user_with_long_password_succeeds(client, auth_headers):
    """Password with more than 8 characters should be accepted."""
    response = client.post(
        "/api/users",
        json={
            "username": "longpass",
            "name": "Long Pass",
            "password": "verylongpassword123456",  # More than 8 characters
            "is_admin": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, f"Should succeed: {response.text}"


def test_change_password_with_7_char_new_password_fails(client, auth_headers):
    """Password change with 7 character new password should fail."""
    response = client.put(
        "/api/users/me/password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "1234567",  # 7 characters
        },
        headers=auth_headers,
    )
    assert response.status_code == 422, "Should fail validation"
    body = response.json()
    assert "detail" in body


def test_change_password_with_8_char_new_password_succeeds(client, auth_headers):
    """Password change with exactly 8 character new password should succeed."""
    response = client.put(
        "/api/users/me/password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "12345678",  # 8 characters
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, f"Should succeed: {response.text}"


def test_change_password_with_long_new_password_succeeds(client, auth_headers):
    """Password change with long new password should succeed."""
    response = client.put(
        "/api/users/me/password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "verylongpassword123456",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, f"Should succeed: {response.text}"
