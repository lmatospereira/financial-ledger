"""POST /api/transfers"""
import pytest


@pytest.fixture()
def checking(client, auth_headers):
    return client.post(
        "/api/accounts",
        json={"name": "Checking", "type": "checking", "color": "#111111"},
        headers=auth_headers,
    ).json()


@pytest.fixture()
def savings(client, auth_headers):
    return client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#222222"},
        headers=auth_headers,
    ).json()


def make_transfer(client, auth_headers, from_id, to_id, **overrides):
    payload = {
        "from_account_id": from_id,
        "to_account_id": to_id,
        "amount": 100.0,
        "date": "2026-03-15",
        "description": "Transfer",
    }
    payload.update(overrides)
    return client.post("/api/transfers", json=payload, headers=auth_headers)


def test_create_transfer(client, auth_headers, checking, savings):
    response = make_transfer(client, auth_headers, checking["id"], savings["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "transfer"
    assert body["account_id"] == checking["id"]
    assert body["to_account_id"] == savings["id"]
    assert body["amount"] == 100.0
    assert body["category_id"] is None


def test_transfer_same_account_rejected(client, auth_headers, checking):
    response = make_transfer(client, auth_headers, checking["id"], checking["id"])
    assert response.status_code == 422


def test_transfer_unknown_source_account(client, auth_headers, savings):
    response = make_transfer(client, auth_headers, 999, savings["id"])
    assert response.status_code == 404


def test_transfer_unknown_destination_account(client, auth_headers, checking):
    response = make_transfer(client, auth_headers, checking["id"], 999)
    assert response.status_code == 404


def test_transfer_negative_amount_rejected(client, auth_headers, checking, savings):
    response = make_transfer(client, auth_headers, checking["id"], savings["id"], amount=-10)
    assert response.status_code == 422


def test_transfer_appears_in_transaction_list(client, auth_headers, checking, savings):
    make_transfer(client, auth_headers, checking["id"], savings["id"], date="2026-03-15")
    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    types = {t["type"] for t in response.json()}
    assert "transfer" in types


def test_transfer_excluded_from_summary_income_expense(client, auth_headers, checking, savings):
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Paycheck",
            "amount": 1000.0,
            "type": "income",
            "category_id": None,
            "account_id": checking["id"],
        },
        headers=auth_headers,
    )
    make_transfer(client, auth_headers, checking["id"], savings["id"], amount=300, date="2026-03-05")

    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    body = response.json()
    assert body["income_total"] == 1000.0
    assert body["expense_total"] == 0.0


def test_transfer_requires_auth(client, checking, savings):
    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": checking["id"],
            "to_account_id": savings["id"],
            "amount": 10.0,
            "date": "2026-03-15",
            "description": "x",
        },
    )
    assert response.status_code == 401


def test_transfer_cannot_be_created_via_transactions_endpoint(client, auth_headers, checking):
    response = client.post(
        "/api/transactions",
        json={
            "date": "2026-03-15",
            "description": "Sneaky transfer",
            "amount": 100.0,
            "type": "transfer",
            "category_id": None,
            "account_id": checking["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
