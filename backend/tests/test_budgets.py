"""Tests for budgets: CRUD operations, duplicate prevention, and status calculation."""
import pytest

from app import auth, crud


@pytest.fixture()
def expense_category(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Groceries", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    )
    return response.json()


@pytest.fixture()
def another_expense_category(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Utilities", "type": "expense", "color": "#00FF00"},
        headers=auth_headers,
    )
    return response.json()


def make_budget(client, auth_headers, category_id, amount=1000.0):
    return client.post(
        "/api/budgets",
        json={"category_id": category_id, "amount": amount},
        headers=auth_headers,
    )


def test_create_budget(client, auth_headers, expense_category):
    response = make_budget(client, auth_headers, expense_category["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["category_id"] == expense_category["id"]
    assert body["amount"] == 1000.0
    assert "id" in body
    assert "created_at" in body


def test_create_budget_invalid_category(client, auth_headers):
    response = make_budget(client, auth_headers, 999)
    assert response.status_code == 404


def test_create_budget_duplicate_category_rejected(client, auth_headers, expense_category):
    # First budget succeeds
    response1 = make_budget(client, auth_headers, expense_category["id"], 500.0)
    assert response1.status_code == 201

    # Second budget for same category should fail
    response2 = make_budget(client, auth_headers, expense_category["id"], 1000.0)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_list_budgets(client, auth_headers, expense_category, another_expense_category):
    make_budget(client, auth_headers, expense_category["id"], 500.0)
    make_budget(client, auth_headers, another_expense_category["id"], 1500.0)

    response = client.get("/api/budgets", headers=auth_headers)
    assert response.status_code == 200
    budgets = response.json()
    assert len(budgets) == 2
    categories = {b["category_id"] for b in budgets}
    assert expense_category["id"] in categories
    assert another_expense_category["id"] in categories


def test_update_budget(client, auth_headers, expense_category):
    created = make_budget(client, auth_headers, expense_category["id"], 500.0).json()
    response = client.put(
        f"/api/budgets/{created['id']}",
        json={"category_id": expense_category["id"], "amount": 2000.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 2000.0


def test_update_budget_not_found(client, auth_headers):
    response = client.put(
        "/api/budgets/999",
        json={"category_id": 1, "amount": 1000.0},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_budget(client, auth_headers, expense_category):
    created = make_budget(client, auth_headers, expense_category["id"]).json()
    response = client.delete(f"/api/budgets/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/budgets", headers=auth_headers)
    assert response.json() == []


def test_delete_budget_not_found(client, auth_headers):
    response = client.delete("/api/budgets/999", headers=auth_headers)
    assert response.status_code == 404


def test_budget_status_with_no_spending(client, auth_headers, expense_category):
    make_budget(client, auth_headers, expense_category["id"], 1000.0)

    response = client.get("/api/budgets/status?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    statuses = response.json()
    assert len(statuses) == 1
    assert statuses[0]["category_id"] == expense_category["id"]
    assert statuses[0]["spent_amount"] == 0.0
    assert statuses[0]["budget_amount"] == 1000.0
    assert statuses[0]["percentage"] == 0.0
    assert statuses[0]["over_budget"] is False


def test_budget_status_with_partial_spending(client, auth_headers, expense_category, default_account):
    make_budget(client, auth_headers, expense_category["id"], 1000.0)

    # Create an expense transaction for 500
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-15",
            "description": "Groceries",
            "amount": 500.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )

    response = client.get("/api/budgets/status?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    statuses = response.json()
    assert len(statuses) == 1
    assert statuses[0]["spent_amount"] == 500.0
    assert statuses[0]["percentage"] == 50.0
    assert statuses[0]["over_budget"] is False


def test_budget_status_over_budget(client, auth_headers, expense_category, default_account):
    make_budget(client, auth_headers, expense_category["id"], 1000.0)

    # Create an expense transaction for 1500 (over budget)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-15",
            "description": "Groceries",
            "amount": 1500.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )

    response = client.get("/api/budgets/status?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    statuses = response.json()
    assert len(statuses) == 1
    assert statuses[0]["spent_amount"] == 1500.0
    assert statuses[0]["percentage"] == 150.0
    assert statuses[0]["over_budget"] is True


def test_budget_status_multiple_budgets(client, auth_headers, expense_category, another_expense_category, default_account):
    make_budget(client, auth_headers, expense_category["id"], 1000.0)
    make_budget(client, auth_headers, another_expense_category["id"], 500.0)

    # Create expenses
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-15",
            "description": "Groceries",
            "amount": 500.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-16",
            "description": "Utilities",
            "amount": 600.0,
            "type": "expense",
            "category_id": another_expense_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )

    response = client.get("/api/budgets/status?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    statuses = response.json()
    assert len(statuses) == 2
    status_by_cat = {s["category_id"]: s for s in statuses}
    assert status_by_cat[expense_category["id"]]["spent_amount"] == 500.0
    assert status_by_cat[expense_category["id"]]["over_budget"] is False
    assert status_by_cat[another_expense_category["id"]]["spent_amount"] == 600.0
    assert status_by_cat[another_expense_category["id"]]["over_budget"] is True


def test_budgets_require_auth(client):
    response = client.get("/api/budgets")
    assert response.status_code == 401


# Cross-user isolation test
@pytest.fixture()
def user_a_budget(client, db_session):
    """Set up user A with a budget."""
    crud.create_user(db_session, username="alice", password_hash=auth.hash_password("alicepass123"))
    response = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    category = client.post(
        "/api/categories",
        json={"name": "Alice Groceries", "type": "expense", "color": "#FF0000"},
        headers=headers,
    ).json()

    budget = client.post(
        "/api/budgets",
        json={"category_id": category["id"], "amount": 1000.0},
        headers=headers,
    ).json()

    return {"headers": headers, "budget": budget, "category": category}


def test_budgets_cross_user_isolation(client, auth_headers, user_a_budget, expense_category):
    # Admin user creates their own budget
    admin_budget = client.post(
        "/api/budgets",
        json={"category_id": expense_category["id"], "amount": 500.0},
        headers=auth_headers,
    ).json()

    # Admin user should only see their own budget
    response = client.get("/api/budgets", headers=auth_headers)
    ids = {b["id"] for b in response.json()}
    assert admin_budget["id"] in ids
    assert user_a_budget["budget"]["id"] not in ids

    # Admin cannot update Alice's budget
    response = client.put(
        f"/api/budgets/{user_a_budget['budget']['id']}",
        json={"category_id": user_a_budget["category"]["id"], "amount": 9999.0},
        headers=auth_headers,
    )
    assert response.status_code == 404

    # Admin cannot delete Alice's budget
    response = client.delete(f"/api/budgets/{user_a_budget['budget']['id']}", headers=auth_headers)
    assert response.status_code == 404
