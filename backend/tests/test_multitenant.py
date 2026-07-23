"""Cross-user isolation: user A must never be able to read, modify, or
delete user B's accounts, categories, or transactions -- including by
guessing IDs. Get/update/delete by a foreign ID must 404, not 403 or 200,
so existence is never leaked.
"""
import pytest

from app import auth, crud


@pytest.fixture()
def user_a(client, db_session):
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
    transaction = client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Alice paycheck",
            "amount": 500.0,
            "type": "income",
            "category_id": category["id"],
            "account_id": account["id"],
        },
        headers=headers,
    ).json()
    return {
        "headers": headers,
        "account": account,
        "category": category,
        "transaction": transaction,
    }


@pytest.fixture()
def user_b(client, db_session):
    crud.create_user(db_session, username="bob", password_hash=auth.hash_password("bobpass123"))
    response = client.post("/api/auth/login", json={"username": "bob", "password": "bobpass123"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    account = client.post(
        "/api/accounts",
        json={"name": "Bob Checking", "type": "checking", "color": "#222222"},
        headers=headers,
    ).json()
    category = client.post(
        "/api/categories",
        json={"name": "Bob Salary", "type": "income", "color": "#0000FF"},
        headers=headers,
    ).json()
    transaction = client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Bob paycheck",
            "amount": 900.0,
            "type": "income",
            "category_id": category["id"],
            "account_id": account["id"],
        },
        headers=headers,
    ).json()
    return {
        "headers": headers,
        "account": account,
        "category": category,
        "transaction": transaction,
    }


# ---------- Accounts ----------
def test_accounts_list_does_not_leak_other_user(client, user_a, user_b):
    response = client.get("/api/accounts", headers=user_a["headers"])
    ids = {a["id"] for a in response.json()}
    assert user_a["account"]["id"] in ids
    assert user_b["account"]["id"] not in ids


def test_accounts_update_foreign_id_404s(client, user_a, user_b):
    response = client.put(
        f"/api/accounts/{user_b['account']['id']}",
        json={"name": "Hijacked", "type": "wallet", "color": "#ffffff"},
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_accounts_delete_foreign_id_404s(client, user_a, user_b):
    response = client.delete(f"/api/accounts/{user_b['account']['id']}", headers=user_a["headers"])
    assert response.status_code == 404
    # Confirm it wasn't actually deleted.
    response = client.get("/api/accounts", headers=user_b["headers"])
    ids = {a["id"] for a in response.json()}
    assert user_b["account"]["id"] in ids


# ---------- Categories ----------
def test_categories_list_does_not_leak_other_user(client, user_a, user_b):
    response = client.get("/api/categories", headers=user_a["headers"])
    ids = {c["id"] for c in response.json()}
    assert user_a["category"]["id"] in ids
    assert user_b["category"]["id"] not in ids


def test_categories_update_foreign_id_404s(client, user_a, user_b):
    response = client.put(
        f"/api/categories/{user_b['category']['id']}",
        json={"name": "Hijacked", "type": "income", "color": "#ffffff"},
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_categories_delete_foreign_id_404s(client, user_a, user_b):
    response = client.delete(f"/api/categories/{user_b['category']['id']}", headers=user_a["headers"])
    assert response.status_code == 404


# ---------- Transactions ----------
def test_transactions_list_does_not_leak_other_user(client, user_a, user_b):
    response = client.get("/api/transactions?month=3&year=2026", headers=user_a["headers"])
    ids = {t["id"] for t in response.json()}
    assert user_a["transaction"]["id"] in ids
    assert user_b["transaction"]["id"] not in ids


def test_transaction_update_foreign_id_404s(client, user_a, user_b):
    response = client.put(
        f"/api/transactions/{user_b['transaction']['id']}",
        json={
            "date": "2026-03-02",
            "description": "Hijacked",
            "amount": 1.0,
            "type": "income",
            "category_id": None,
            "account_id": user_a["account"]["id"],
        },
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_transaction_delete_foreign_id_404s(client, user_a, user_b):
    response = client.delete(f"/api/transactions/{user_b['transaction']['id']}", headers=user_a["headers"])
    assert response.status_code == 404
    response = client.get("/api/transactions?month=3&year=2026", headers=user_b["headers"])
    ids = {t["id"] for t in response.json()}
    assert user_b["transaction"]["id"] in ids


def test_cannot_create_transaction_against_foreign_account(client, user_a, user_b):
    response = client.post(
        "/api/transactions",
        json={
            "date": "2026-03-02",
            "description": "Sneaky",
            "amount": 1.0,
            "type": "income",
            "category_id": None,
            "account_id": user_b["account"]["id"],
        },
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_cannot_create_transaction_against_foreign_category(client, user_a, user_b):
    response = client.post(
        "/api/transactions",
        json={
            "date": "2026-03-02",
            "description": "Sneaky",
            "amount": 1.0,
            "type": "income",
            "category_id": user_b["category"]["id"],
            "account_id": user_a["account"]["id"],
        },
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_transactions_filter_by_foreign_account_id_404s(client, user_a, user_b):
    response = client.get(
        f"/api/transactions?month=3&year=2026&account_id={user_b['account']['id']}",
        headers=user_a["headers"],
    )
    assert response.status_code == 404


# ---------- Transfers ----------
def test_transfer_rejects_foreign_source_account(client, user_a, user_b):
    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": user_b["account"]["id"],
            "to_account_id": user_a["account"]["id"],
            "amount": 10.0,
            "date": "2026-03-05",
            "description": "Sneaky",
        },
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_transfer_rejects_foreign_destination_account(client, user_a, user_b):
    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": user_a["account"]["id"],
            "to_account_id": user_b["account"]["id"],
            "amount": 10.0,
            "date": "2026-03-05",
            "description": "Sneaky",
        },
        headers=user_a["headers"],
    )
    assert response.status_code == 404


# ---------- Summary & reports ----------
def test_summary_does_not_mix_user_data(client, user_a, user_b):
    response = client.get("/api/summary?month=3&year=2026", headers=user_a["headers"])
    body = response.json()
    assert body["income_total"] == 500.0  # only Alice's transaction, not Bob's 900

    response = client.get("/api/summary?month=3&year=2026", headers=user_b["headers"])
    body = response.json()
    assert body["income_total"] == 900.0


def test_summary_account_filter_rejects_foreign_account(client, user_a, user_b):
    response = client.get(
        f"/api/summary?month=3&year=2026&account_id={user_b['account']['id']}",
        headers=user_a["headers"],
    )
    assert response.status_code == 404


def test_monthly_trend_does_not_mix_user_data(client, user_a, user_b):
    response = client.get("/api/reports/monthly-trend?year=2026", headers=user_a["headers"])
    march = {m["month"]: m for m in response.json()}[3]
    assert march["income_total"] == 500.0


def test_by_category_does_not_mix_user_data(client, user_a, user_b):
    # Both fixtures' seeded transactions are type="income", so an expense
    # transaction is added here per user to exercise the report meaningfully.
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-02",
            "description": "Alice expense",
            "amount": 40.0,
            "type": "expense",
            "category_id": user_a["category"]["id"],
            "account_id": user_a["account"]["id"],
        },
        headers=user_a["headers"],
    )
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-02",
            "description": "Bob expense",
            "amount": 999.0,
            "type": "expense",
            "category_id": user_b["category"]["id"],
            "account_id": user_b["account"]["id"],
        },
        headers=user_b["headers"],
    )

    response = client.get("/api/reports/by-category?month=3&year=2026", headers=user_a["headers"])
    body = response.json()
    assert len(body) == 1
    assert body[0]["category_id"] == user_a["category"]["id"]
    assert body[0]["total"] == 40.0


# ---------- Users (admin scoping, not ownership, but still worth a check) ----------
def test_regular_user_cannot_list_other_users(client, user_a, user_b):
    response = client.get("/api/users", headers=user_a["headers"])
    assert response.status_code == 403
