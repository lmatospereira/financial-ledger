"""GET/POST/PUT/DELETE /api/accounts, including balance computation and the
block-delete-if-has-transactions rule.
"""
import pytest


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


def make_account(client, auth_headers, name="Checking", type_="checking", color="#123456"):
    return client.post(
        "/api/accounts", json={"name": name, "type": type_, "color": color}, headers=auth_headers
    )


def test_create_account(client, auth_headers):
    response = make_account(client, auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Checking"
    assert body["type"] == "checking"
    assert body["balance"] == 0.0
    assert "id" in body


def test_create_account_invalid_type(client, auth_headers):
    response = client.post(
        "/api/accounts",
        json={"name": "Bad", "type": "bitcoin", "color": "#123456"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_account_invalid_color(client, auth_headers):
    response = client.post(
        "/api/accounts",
        json={"name": "Bad", "type": "checking", "color": "not-a-color"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_list_accounts(client, auth_headers):
    make_account(client, auth_headers, name="Checking")
    make_account(client, auth_headers, name="Savings", type_="savings")
    response = client.get("/api/accounts", headers=auth_headers)
    assert response.status_code == 200
    names = {a["name"] for a in response.json()}
    assert names == {"Checking", "Savings"}


def test_update_account(client, auth_headers):
    created = make_account(client, auth_headers).json()
    response = client.put(
        f"/api/accounts/{created['id']}",
        json={"name": "Renamed", "type": "wallet", "color": "#654321"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["type"] == "wallet"


def test_update_account_not_found(client, auth_headers):
    response = client.put(
        "/api/accounts/999",
        json={"name": "Renamed", "type": "wallet", "color": "#654321"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_account(client, auth_headers):
    created = make_account(client, auth_headers).json()
    response = client.delete(f"/api/accounts/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/accounts", headers=auth_headers)
    assert response.json() == []


def test_delete_account_not_found(client, auth_headers):
    response = client.delete("/api/accounts/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_account_with_transactions_blocked(client, auth_headers, income_category):
    account = make_account(client, auth_headers).json()
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Paycheck",
            "amount": 100.0,
            "type": "income",
            "category_id": income_category["id"],
            "account_id": account["id"],
        },
        headers=auth_headers,
    )
    response = client.delete(f"/api/accounts/{account['id']}", headers=auth_headers)
    assert response.status_code == 409

    # Still listed, untouched.
    response = client.get("/api/accounts", headers=auth_headers)
    assert len(response.json()) == 1


def test_accounts_require_auth(client):
    response = client.get("/api/accounts")
    assert response.status_code == 401


# ---------- Balance computation ----------
def test_account_balance_income_and_expense(client, auth_headers, income_category, expense_category):
    account = make_account(client, auth_headers).json()
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Paycheck",
            "amount": 1000.0,
            "type": "income",
            "category_id": income_category["id"],
            "account_id": account["id"],
        },
        headers=auth_headers,
    )
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-02",
            "description": "Groceries",
            "amount": 200.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": account["id"],
        },
        headers=auth_headers,
    )

    response = client.get("/api/accounts", headers=auth_headers)
    body = response.json()
    assert len(body) == 1
    assert body[0]["balance"] == 800.0


def test_account_balance_reflects_transfers(client, auth_headers):
    checking = make_account(client, auth_headers, name="Checking").json()
    savings = make_account(client, auth_headers, name="Savings", type_="savings").json()

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
    client.post(
        "/api/transfers",
        json={
            "from_account_id": checking["id"],
            "to_account_id": savings["id"],
            "amount": 300.0,
            "date": "2026-03-05",
            "description": "Move to savings",
        },
        headers=auth_headers,
    )

    accounts = {a["id"]: a for a in client.get("/api/accounts", headers=auth_headers).json()}
    assert accounts[checking["id"]]["balance"] == 700.0
    assert accounts[savings["id"]]["balance"] == 300.0
