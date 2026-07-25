"""Tests for recurring transactions: CRUD operations, generation logic, and idempotency."""
import pytest

from app import auth, crud


@pytest.fixture()
def income_category(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Salary", "type": "income", "color": "#00FF00"},
        headers=auth_headers,
    )
    return response.json()


@pytest.fixture()
def expense_category(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Rent", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    )
    return response.json()


def make_recurring_transaction(
    client,
    auth_headers,
    account_id,
    category_id=None,
    description="Recurring transaction",
    amount=1000.0,
    type_="income",
    day_of_month=15,
    start_date="2026-01-01",
    end_date=None,
):
    payload = {
        "account_id": account_id,
        "category_id": category_id,
        "description": description,
        "amount": amount,
        "type": type_,
        "day_of_month": day_of_month,
        "start_date": start_date,
        "end_date": end_date,
    }
    return client.post("/api/recurring-transactions", json=payload, headers=auth_headers)


def test_create_recurring_transaction(client, auth_headers, default_account, income_category):
    response = make_recurring_transaction(
        client, auth_headers, default_account["id"], income_category["id"], amount=5000.0
    )
    assert response.status_code == 201
    body = response.json()
    assert body["account_id"] == default_account["id"]
    assert body["category_id"] == income_category["id"]
    assert body["amount"] == 5000.0
    assert body["type"] == "income"
    assert body["day_of_month"] == 15
    assert body["active"] is True
    assert "id" in body
    assert "created_at" in body


def test_create_recurring_transaction_invalid_account(client, auth_headers, income_category):
    response = make_recurring_transaction(client, auth_headers, 999, income_category["id"])
    assert response.status_code == 404


def test_create_recurring_transaction_invalid_category(client, auth_headers, default_account):
    response = make_recurring_transaction(client, auth_headers, default_account["id"], 999)
    assert response.status_code == 404


def test_create_recurring_transaction_no_category(client, auth_headers, default_account):
    response = make_recurring_transaction(client, auth_headers, default_account["id"], None)
    assert response.status_code == 201
    body = response.json()
    assert body["category_id"] is None


def test_list_recurring_transactions(client, auth_headers, default_account, income_category, expense_category):
    make_recurring_transaction(
        client, auth_headers, default_account["id"], income_category["id"], amount=5000.0
    )
    make_recurring_transaction(
        client, auth_headers, default_account["id"], expense_category["id"], type_="expense", amount=1000.0
    )

    response = client.get("/api/recurring-transactions", headers=auth_headers)
    assert response.status_code == 200
    rts = response.json()
    assert len(rts) == 2


def test_update_recurring_transaction(client, auth_headers, default_account, income_category):
    created = make_recurring_transaction(
        client, auth_headers, default_account["id"], income_category["id"], amount=5000.0
    ).json()

    response = client.put(
        f"/api/recurring-transactions/{created['id']}",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Updated",
            "amount": 6000.0,
            "type": "income",
            "day_of_month": 20,
            "start_date": "2026-01-01",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 6000.0
    assert body["day_of_month"] == 20


def test_update_recurring_transaction_toggle_active(client, auth_headers, default_account, income_category):
    created = make_recurring_transaction(
        client, auth_headers, default_account["id"], income_category["id"]
    ).json()

    response = client.put(
        f"/api/recurring-transactions/{created['id']}",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Test",
            "amount": 1000.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-01-01",
            "end_date": None,
            "active": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["active"] is False


def test_delete_recurring_transaction(client, auth_headers, default_account, income_category):
    created = make_recurring_transaction(
        client, auth_headers, default_account["id"], income_category["id"]
    ).json()

    response = client.delete(
        f"/api/recurring-transactions/{created['id']}", headers=auth_headers
    )
    assert response.status_code == 204

    response = client.get("/api/recurring-transactions", headers=auth_headers)
    assert response.json() == []


def test_recurring_transactions_require_auth(client):
    response = client.get("/api/recurring-transactions")
    assert response.status_code == 401


# ---------- Generation Tests ----------
def test_recurring_transaction_generation_simple(client, auth_headers, default_account, income_category, db_session):
    """Create a recurring transaction and verify it generates transactions."""
    rt_response = make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=15,
        start_date="2026-03-01",
        end_date=None,
    )
    assert rt_response.status_code == 201

    # Call list_transactions to trigger generation
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["amount"] == 5000.0
    assert transactions[0]["date"] == "2026-03-15"
    assert transactions[0]["recurring_transaction_id"] is not None


def test_recurring_transaction_generation_idempotent(client, auth_headers, default_account, income_category):
    """Calling list_transactions multiple times should not create duplicate transactions."""
    make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=15,
        start_date="2026-03-01",
    )

    # Call list_transactions twice
    response1 = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert len(response1.json()) == 1

    response2 = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert len(response2.json()) == 1

    # Call for a different month to ensure it doesn't re-generate
    response3 = client.get("/api/transactions?month=4&year=2026", headers=auth_headers)
    transactions = response3.json()
    assert len(transactions) == 1
    assert transactions[0]["date"] == "2026-04-15"


def test_recurring_transaction_skips_before_start_date(client, auth_headers, default_account, income_category):
    """Recurring transactions should not generate before start_date."""
    make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=15,
        start_date="2026-05-01",
    )

    # Try to fetch March transactions
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    transactions = response.json()
    assert len(transactions) == 0


def test_recurring_transaction_skips_after_end_date(client, auth_headers, default_account, income_category):
    """Recurring transactions should not generate after end_date."""
    make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=15,
        start_date="2026-01-01",
        end_date="2026-02-28",
    )

    # Try to fetch March transactions
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    transactions = response.json()
    assert len(transactions) == 0

    # February should have it
    response = client.get("/api/transactions?month=2&year=2026", headers=auth_headers)
    transactions = response.json()
    assert len(transactions) == 1


def test_recurring_transaction_inactive_not_generated(client, auth_headers, default_account, income_category):
    """Inactive recurring transactions should not generate."""
    rt_response = make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=15,
        start_date="2026-03-01",
    )
    rt_id = rt_response.json()["id"]

    # Deactivate it
    client.put(
        f"/api/recurring-transactions/{rt_id}",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Test",
            "amount": 5000.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-03-01",
            "end_date": None,
            "active": False,
        },
        headers=auth_headers,
    )

    # Try to fetch transactions
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    transactions = response.json()
    assert len(transactions) == 0


def test_recurring_transaction_day_of_month_clamping_short_month(client, auth_headers, default_account, income_category):
    """day_of_month=31 should clamp to last day in months with < 31 days."""
    make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=31,
        start_date="2026-01-01",
    )

    # February 2026 has 28 days, so should generate on 28th
    response = client.get("/api/transactions?month=2&year=2026", headers=auth_headers)
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["date"] == "2026-02-28"

    # March 2026 has 31 days, so should generate on 31st
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["date"] == "2026-03-31"


def test_recurring_transaction_multiple_months(client, auth_headers, default_account, income_category):
    """Recurring transaction should generate across multiple months."""
    make_recurring_transaction(
        client,
        auth_headers,
        default_account["id"],
        income_category["id"],
        amount=5000.0,
        type_="income",
        day_of_month=15,
        start_date="2026-01-01",
        end_date="2026-12-31",
    )

    # Fetch March transactions
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    march_transactions = response.json()
    assert len(march_transactions) == 1
    assert march_transactions[0]["date"] == "2026-03-15"

    # Fetch April transactions
    response = client.get("/api/transactions?month=4&year=2026", headers=auth_headers)
    april_transactions = response.json()
    assert len(april_transactions) == 1
    assert april_transactions[0]["date"] == "2026-04-15"

    # Both should be linked to the same recurring transaction
    assert march_transactions[0]["recurring_transaction_id"] == april_transactions[0]["recurring_transaction_id"]


# Cross-user isolation test
@pytest.fixture()
def user_a_recurring(client, db_session):
    """Set up user A with a recurring transaction."""
    crud.create_user(db_session, username="alice", password_hash=auth.hash_password("alicepass123"))
    response = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    account = client.post(
        "/api/accounts",
        json={"name": "Alice Checking", "type": "checking", "color": "#111111"},
        headers=headers,
    ).json()

    category = client.post(
        "/api/categories",
        json={"name": "Alice Salary", "type": "income", "color": "#00FF00"},
        headers=headers,
    ).json()

    rt = make_recurring_transaction(
        client, headers, account["id"], category["id"], amount=5000.0
    ).json()

    return {"headers": headers, "rt": rt}


def test_recurring_transactions_cross_user_isolation(client, auth_headers, user_a_recurring, default_account, income_category):
    # Admin user creates their own recurring transaction
    admin_rt = make_recurring_transaction(
        client, auth_headers, default_account["id"], income_category["id"], amount=3000.0
    ).json()

    # Admin user should only see their own recurring transaction
    response = client.get("/api/recurring-transactions", headers=auth_headers)
    ids = {rt["id"] for rt in response.json()}
    assert admin_rt["id"] in ids
    assert user_a_recurring["rt"]["id"] not in ids

    # Admin cannot update Alice's recurring transaction
    response = client.put(
        f"/api/recurring-transactions/{user_a_recurring['rt']['id']}",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Hijacked",
            "amount": 99999.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-01-01",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404

    # Admin cannot delete Alice's recurring transaction
    response = client.delete(
        f"/api/recurring-transactions/{user_a_recurring['rt']['id']}", headers=auth_headers
    )
    assert response.status_code == 404
