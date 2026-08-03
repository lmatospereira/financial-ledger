"""Tests for transaction pending/confirmed status feature."""
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
        json={"name": "Groceries", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    )
    return response.json()


def make_transaction(client, auth_headers, category_id, account_id=None, **overrides):
    payload = {
        "date": "2026-03-15",
        "description": "Test transaction",
        "amount": 100.0,
        "type": "income",
        "category_id": category_id,
        "account_id": account_id,
    }
    payload.update(overrides)
    return client.post("/api/transactions", json=payload, headers=auth_headers)


# ---------- Creating pending transactions ----------
def test_create_transaction_with_pending_status(client, auth_headers, income_category, default_account):
    """Verify that a transaction can be created with status='pending'."""
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], status="pending"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"


def test_create_transaction_defaults_to_confirmed(client, auth_headers, income_category, default_account):
    """Backward compatibility: transaction created without specifying status defaults to 'confirmed'."""
    response = make_transaction(client, auth_headers, income_category["id"], default_account["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"


# ---------- Pending transactions excluded from balance/summary ----------
def test_pending_transaction_excluded_from_account_balance(client, auth_headers, income_category, default_account):
    """Confirm that pending transactions do not count toward account balance."""
    # Create a confirmed transaction
    confirmed_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=100.0
    ).json()
    assert confirmed_tx["status"] == "confirmed"

    # Create a pending transaction
    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=50.0, status="pending"
    ).json()
    assert pending_tx["status"] == "pending"

    # Get account balance
    response = client.get("/api/accounts", headers=auth_headers)
    accounts = response.json()
    assert len(accounts) == 1
    # Only the confirmed transaction (100) counts
    assert accounts[0]["balance"] == 100.0


def test_pending_transaction_excluded_from_summary(client, auth_headers, income_category, default_account):
    """Confirm that pending transactions are excluded from monthly summary."""
    # Create a confirmed income transaction
    make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=200.0
    )

    # Create a pending income transaction
    make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=50.0, status="pending"
    )

    # Get summary
    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    summary = response.json()
    # Only the confirmed transaction (200) counts
    assert summary["income_total"] == 200.0
    assert summary["balance"] == 200.0
    assert summary["previous_balance"] == 0.0


# ---------- Transaction listing with status filter ----------
def test_list_transactions_includes_pending_by_default(client, auth_headers, income_category, default_account):
    """Without a status filter, list_transactions returns both confirmed and pending."""
    confirmed_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-10"
    ).json()

    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-15", status="pending"
    ).json()

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 2
    ids = {t["id"] for t in transactions}
    assert confirmed_tx["id"] in ids
    assert pending_tx["id"] in ids


def test_filter_transactions_by_confirmed_status(client, auth_headers, income_category, default_account):
    """Filter transactions by status=confirmed."""
    confirmed_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-10"
    ).json()

    make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-15", status="pending"
    )

    response = client.get("/api/transactions?month=3&year=2026&status=confirmed", headers=auth_headers)
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["id"] == confirmed_tx["id"]
    assert transactions[0]["status"] == "confirmed"


def test_filter_transactions_by_pending_status(client, auth_headers, income_category, default_account):
    """Filter transactions by status=pending."""
    make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-10"
    )

    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-15", status="pending"
    ).json()

    response = client.get("/api/transactions?month=3&year=2026&status=pending", headers=auth_headers)
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["id"] == pending_tx["id"]
    assert transactions[0]["status"] == "pending"


# ---------- Confirm transaction endpoint ----------
def test_confirm_transaction(client, auth_headers, income_category, default_account):
    """Verify that confirming a pending transaction updates its status and makes it count toward balance."""
    # Create a pending transaction
    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=100.0, status="pending"
    ).json()

    # Verify it doesn't count in balance yet
    response = client.get("/api/accounts", headers=auth_headers)
    assert response.json()[0]["balance"] == 0.0

    # Confirm the transaction
    response = client.post(
        f"/api/transactions/{pending_tx['id']}/confirm", headers=auth_headers
    )
    assert response.status_code == 200
    confirmed_tx = response.json()
    assert confirmed_tx["status"] == "confirmed"
    assert confirmed_tx["id"] == pending_tx["id"]

    # Verify it now counts in balance
    response = client.get("/api/accounts", headers=auth_headers)
    assert response.json()[0]["balance"] == 100.0


def test_confirm_transaction_not_found(client, auth_headers):
    """Confirm a nonexistent transaction returns 404."""
    response = client.post("/api/transactions/999/confirm", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_confirm_already_confirmed_transaction(client, auth_headers, income_category, default_account):
    """Confirming an already-confirmed transaction returns 409."""
    # Create a confirmed transaction
    confirmed_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"]
    ).json()

    # Try to confirm it again
    response = client.post(
        f"/api/transactions/{confirmed_tx['id']}/confirm", headers=auth_headers
    )
    assert response.status_code == 409
    assert "already confirmed" in response.json()["detail"].lower()


def test_confirm_updates_summary_totals(client, auth_headers, expense_category, default_account):
    """Confirming a transaction updates summary totals."""
    # Create a pending expense
    pending_tx = make_transaction(
        client, auth_headers, expense_category["id"], default_account["id"],
        type="expense", amount=75.0, status="pending"
    ).json()

    # Summary shouldn't reflect it yet
    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    summary = response.json()
    assert summary["expense_total"] == 0.0

    # Confirm it
    client.post(f"/api/transactions/{pending_tx['id']}/confirm", headers=auth_headers)

    # Summary should now reflect it
    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    summary = response.json()
    assert summary["expense_total"] == 75.0
    assert summary["balance"] == -75.0


# ---------- Cross-user isolation ----------
@pytest.fixture()
def user_a_pending_transaction(client, db_session):
    """Set up user A with a pending transaction."""
    crud.create_user(db_session, username="alice", name="Alice", password_hash=auth.hash_password("alicepass123"))
    response = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    account = client.post(
        "/api/accounts",
        json={"name": "Alice Account", "type": "checking", "color": "#123456"},
        headers=headers,
    ).json()

    category = client.post(
        "/api/categories",
        json={"name": "Alice Income", "type": "income", "color": "#00FF00"},
        headers=headers,
    ).json()

    tx = client.post(
        "/api/transactions",
        json={
            "date": "2026-03-15",
            "description": "Alice Transaction",
            "amount": 100.0,
            "type": "income",
            "category_id": category["id"],
            "account_id": account["id"],
            "status": "pending",
        },
        headers=headers,
    ).json()

    return {"headers": headers, "transaction": tx}


def test_confirm_another_users_transaction_returns_404(client, auth_headers, user_a_pending_transaction):
    """Admin cannot confirm Alice's transaction; it returns 404."""
    response = client.post(
        f"/api/transactions/{user_a_pending_transaction['transaction']['id']}/confirm",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_transaction_status_cross_user_isolation(client, auth_headers, user_a_pending_transaction, income_category, default_account):
    """Admin's confirmed transactions don't appear when Alice filters by status."""
    # Admin creates a confirmed transaction
    admin_confirmed = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-10"
    ).json()

    # Admin filters by confirmed (should see only their own)
    response = client.get("/api/transactions?month=3&year=2026&status=confirmed", headers=auth_headers)
    admin_txs = response.json()
    assert len(admin_txs) == 1
    assert admin_txs[0]["id"] == admin_confirmed["id"]

    # Alice filters by confirmed (should see nothing yet)
    response = client.get("/api/transactions?month=3&year=2026&status=confirmed", headers=user_a_pending_transaction["headers"])
    alice_txs = response.json()
    assert len(alice_txs) == 0

    # Alice filters by pending (should see their own)
    response = client.get("/api/transactions?month=3&year=2026&status=pending", headers=user_a_pending_transaction["headers"])
    alice_txs = response.json()
    assert len(alice_txs) == 1
    assert alice_txs[0]["id"] == user_a_pending_transaction["transaction"]["id"]


# ---------- Confirm with account switch (pay-at-confirm-time) ----------
@pytest.fixture()
def second_account(client, auth_headers):
    response = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#0000FF"},
        headers=auth_headers,
    )
    return response.json()


def test_confirm_with_account_switch(client, auth_headers, income_category, default_account, second_account):
    """Confirming with an account_id reassigns the transaction to that account."""
    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=100.0, status="pending"
    ).json()

    response = client.post(
        f"/api/transactions/{pending_tx['id']}/confirm",
        json={"account_id": second_account["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    confirmed_tx = response.json()
    assert confirmed_tx["status"] == "confirmed"
    assert confirmed_tx["account_id"] == second_account["id"]

    # Balance moved to the new account, not the original one.
    accounts_by_id = {a["id"]: a for a in client.get("/api/accounts", headers=auth_headers).json()}
    assert accounts_by_id[second_account["id"]]["balance"] == 100.0
    assert accounts_by_id[default_account["id"]]["balance"] == 0.0


def test_confirm_with_account_switch_invalid_account(client, auth_headers, income_category, default_account):
    """Confirming with an account_id the user doesn't own returns 404."""
    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], status="pending"
    ).json()

    response = client.post(
        f"/api/transactions/{pending_tx['id']}/confirm",
        json={"account_id": 999},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_confirm_without_account_keeps_original(client, auth_headers, income_category, default_account):
    """Confirming with no body (or account_id omitted) keeps the original account."""
    pending_tx = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], status="pending"
    ).json()

    response = client.post(
        f"/api/transactions/{pending_tx['id']}/confirm",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["account_id"] == default_account["id"]
