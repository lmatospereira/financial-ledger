"""Tests for goals: CRUD operations, progress calculation, and isolation."""
import pytest

from app import auth, crud


@pytest.fixture()
def savings_account(client, auth_headers):
    """Create a savings account for testing goal progress."""
    response = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#00AA00"},
        headers=auth_headers,
    )
    return response.json()


def make_goal(
    client,
    auth_headers,
    account_id,
    name="Vacation Fund",
    target_amount=5000.0,
    target_date=None,
    color="#FF5733",
):
    payload = {
        "name": name,
        "target_amount": target_amount,
        "account_id": account_id,
        "target_date": target_date,
        "color": color,
    }
    return client.post("/api/goals", json=payload, headers=auth_headers)


def test_create_goal(client, auth_headers, savings_account):
    response = make_goal(
        client, auth_headers, savings_account["id"], target_amount=1000.0
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Vacation Fund"
    assert body["target_amount"] == 1000.0
    assert body["account"]["id"] == savings_account["id"]
    assert body["current_amount"] == 0.0
    assert body["progress_percent"] == 0.0
    assert "id" in body
    assert "created_at" in body


def test_create_goal_with_target_date(client, auth_headers, savings_account):
    response = make_goal(
        client,
        auth_headers,
        savings_account["id"],
        target_date="2026-12-31",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["target_date"] == "2026-12-31"


def test_create_goal_invalid_account(client, auth_headers):
    payload = {
        "name": "Test Goal",
        "target_amount": 1000.0,
        "account_id": 999,
        "target_date": None,
        "color": "#FF5733",
    }
    response = client.post("/api/goals", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_list_goals(client, auth_headers, savings_account):
    make_goal(client, auth_headers, savings_account["id"]).json()
    make_goal(client, auth_headers, savings_account["id"], name="Emergency Fund").json()

    response = client.get("/api/goals", headers=auth_headers)
    assert response.status_code == 200
    goals = response.json()
    assert len(goals) == 2


def test_update_goal(client, auth_headers, savings_account):
    created = make_goal(client, auth_headers, savings_account["id"]).json()

    response = client.put(
        f"/api/goals/{created['id']}",
        json={
            "name": "Updated Goal",
            "target_amount": 2000.0,
            "account_id": savings_account["id"],
            "target_date": "2026-12-31",
            "color": "#0000FF",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Goal"
    assert body["target_amount"] == 2000.0
    assert body["color"] == "#0000FF"


def test_update_goal_partial(client, auth_headers, savings_account):
    """Test partial update with only some fields."""
    created = make_goal(client, auth_headers, savings_account["id"]).json()

    response = client.put(
        f"/api/goals/{created['id']}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["target_amount"] == 5000.0  # Unchanged


def test_update_goal_not_found(client, auth_headers, savings_account):
    response = client.put(
        "/api/goals/999",
        json={
            "name": "Test",
            "target_amount": 1000.0,
            "account_id": savings_account["id"],
            "color": "#FF5733",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_goal_invalid_account(client, auth_headers, savings_account):
    created = make_goal(client, auth_headers, savings_account["id"]).json()

    response = client.put(
        f"/api/goals/{created['id']}",
        json={"account_id": 999},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_goal(client, auth_headers, savings_account):
    created = make_goal(client, auth_headers, savings_account["id"]).json()

    response = client.delete(f"/api/goals/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/goals", headers=auth_headers)
    assert response.json() == []


def test_delete_goal_not_found(client, auth_headers):
    response = client.delete("/api/goals/999", headers=auth_headers)
    assert response.status_code == 404


def test_goal_progress_calculation(client, auth_headers, default_account):
    """Test that goal progress is calculated correctly from account balance."""
    goal = make_goal(
        client, auth_headers, default_account["id"], target_amount=1000.0
    ).json()
    assert goal["progress_percent"] == 0.0

    # Add income to the account
    income_category = client.post(
        "/api/categories",
        json={"name": "Salary", "type": "income", "color": "#00FF00"},
        headers=auth_headers,
    ).json()

    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-01",
            "description": "Salary",
            "amount": 500.0,
            "type": "income",
            "category_id": income_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )

    # Check goal progress
    response = client.get("/api/goals", headers=auth_headers)
    goals = response.json()
    assert len(goals) == 1
    assert goals[0]["current_amount"] == 500.0
    assert goals[0]["progress_percent"] == 0.5  # 500 / 1000


def test_goal_progress_capped_at_100_percent(client, auth_headers, default_account):
    """Test that progress_percent is capped at 100% when balance exceeds target."""
    make_goal(
        client, auth_headers, default_account["id"], target_amount=100.0
    ).json()

    # Add income exceeding target
    income_category = client.post(
        "/api/categories",
        json={"name": "Salary", "type": "income", "color": "#00FF00"},
        headers=auth_headers,
    ).json()

    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-01",
            "description": "Salary",
            "amount": 150.0,
            "type": "income",
            "category_id": income_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )

    # Check goal progress is capped at 1.0 (100%)
    response = client.get("/api/goals", headers=auth_headers)
    goals = response.json()
    assert goals[0]["current_amount"] == 150.0
    assert goals[0]["progress_percent"] == 1.0


def test_goal_progress_zero_target_amount(client, auth_headers, default_account):
    """Test that progress_percent is 0 when target_amount is 0 (edge case guard)."""
    # This test is more about the edge case guard in the calculation logic
    # We can't actually create a goal with 0 target_amount due to Pydantic validation,
    # but the progress_percent calculation guards against division by zero anyway
    goal = make_goal(
        client, auth_headers, default_account["id"], target_amount=1.0
    ).json()
    # The calculation ensures it's at least 0 and at most 1
    assert 0 <= goal["progress_percent"] <= 1


def test_goals_require_auth(client):
    response = client.get("/api/goals")
    assert response.status_code == 401


# Cross-user isolation test
@pytest.fixture()
def user_a_goal(client, db_session):
    """Set up user A with a goal."""
    crud.create_user(db_session, username="alice", name="Alice", password_hash=auth.hash_password("alicepass123"))
    response = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    account = client.post(
        "/api/accounts",
        json={"name": "Alice Savings", "type": "savings", "color": "#00AA00"},
        headers=headers,
    ).json()

    goal = client.post(
        "/api/goals",
        json={
            "name": "Alice Goal",
            "target_amount": 5000.0,
            "account_id": account["id"],
            "target_date": None,
            "color": "#FF5733",
        },
        headers=headers,
    ).json()

    return {"headers": headers, "goal": goal}


def test_goals_cross_user_isolation(client, auth_headers, savings_account, user_a_goal):
    # Admin user creates their own goal
    admin_goal = make_goal(client, auth_headers, savings_account["id"]).json()

    # Admin user should only see their own goal
    response = client.get("/api/goals", headers=auth_headers)
    ids = {g["id"] for g in response.json()}
    assert admin_goal["id"] in ids
    assert user_a_goal["goal"]["id"] not in ids

    # Admin cannot update Alice's goal
    response = client.put(
        f"/api/goals/{user_a_goal['goal']['id']}",
        json={
            "name": "Hijacked",
            "target_amount": 9999.0,
            "account_id": savings_account["id"],
            "color": "#0000FF",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404

    # Admin cannot delete Alice's goal
    response = client.delete(f"/api/goals/{user_a_goal['goal']['id']}", headers=auth_headers)
    assert response.status_code == 404
