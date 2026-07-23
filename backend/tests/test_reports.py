"""GET /api/reports/monthly-trend, GET /api/reports/by-category"""
import pytest


@pytest.fixture()
def account(client, auth_headers):
    return client.post(
        "/api/accounts",
        json={"name": "Checking", "type": "checking", "color": "#111111"},
        headers=auth_headers,
    ).json()


@pytest.fixture()
def income_category(client, auth_headers):
    return client.post(
        "/api/categories",
        json={"name": "Salary", "type": "income", "color": "#00FF00"},
        headers=auth_headers,
    ).json()


@pytest.fixture()
def groceries_category(client, auth_headers):
    return client.post(
        "/api/categories",
        json={"name": "Groceries", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    ).json()


@pytest.fixture()
def rent_category(client, auth_headers):
    return client.post(
        "/api/categories",
        json={"name": "Rent", "type": "expense", "color": "#0000FF"},
        headers=auth_headers,
    ).json()


def make_transaction(client, auth_headers, account_id, category_id, **overrides):
    payload = {
        "date": "2026-03-15",
        "description": "Test",
        "amount": 100.0,
        "type": "income",
        "category_id": category_id,
        "account_id": account_id,
    }
    payload.update(overrides)
    return client.post("/api/transactions", json=payload, headers=auth_headers)


# ---------- monthly-trend ----------
def test_monthly_trend_covers_all_twelve_months(client, auth_headers):
    response = client.get("/api/reports/monthly-trend?year=2026", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 12
    assert [m["month"] for m in body] == list(range(1, 13))
    assert all(m["income_total"] == 0.0 and m["expense_total"] == 0.0 for m in body)


def test_monthly_trend_with_data(client, auth_headers, account, income_category, groceries_category):
    make_transaction(client, auth_headers, account["id"], income_category["id"], date="2026-03-05", amount=1000, type="income")
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-10", amount=200, type="expense")
    make_transaction(client, auth_headers, account["id"], income_category["id"], date="2026-05-01", amount=500, type="income")

    response = client.get("/api/reports/monthly-trend?year=2026", headers=auth_headers)
    body = {m["month"]: m for m in response.json()}
    assert body[3]["income_total"] == 1000.0
    assert body[3]["expense_total"] == 200.0
    assert body[5]["income_total"] == 500.0
    assert body[5]["expense_total"] == 0.0
    assert body[1]["income_total"] == 0.0


def test_monthly_trend_excludes_transfers(client, auth_headers, account):
    other = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#222222"},
        headers=auth_headers,
    ).json()
    make_transaction(client, auth_headers, account["id"], None, date="2026-03-01", amount=1000, type="income")
    client.post(
        "/api/transfers",
        json={
            "from_account_id": account["id"],
            "to_account_id": other["id"],
            "amount": 400.0,
            "date": "2026-03-05",
            "description": "Move",
        },
        headers=auth_headers,
    )

    response = client.get("/api/reports/monthly-trend?year=2026", headers=auth_headers)
    march = {m["month"]: m for m in response.json()}[3]
    assert march["income_total"] == 1000.0
    assert march["expense_total"] == 0.0


def test_monthly_trend_requires_auth(client):
    response = client.get("/api/reports/monthly-trend?year=2026")
    assert response.status_code == 401


# ---------- by-category ----------
def test_by_category_basic(client, auth_headers, account, groceries_category, rent_category):
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-05", amount=150, type="expense")
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-10", amount=50, type="expense")
    make_transaction(client, auth_headers, account["id"], rent_category["id"], date="2026-03-01", amount=1200, type="expense")

    response = client.get("/api/reports/by-category?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    by_id = {c["category_id"]: c for c in response.json()}
    assert by_id[groceries_category["id"]]["total"] == 200.0
    assert by_id[groceries_category["id"]]["name"] == "Groceries"
    assert by_id[rent_category["id"]]["total"] == 1200.0


def test_by_category_omits_categories_with_no_expenses(client, auth_headers, account, groceries_category, rent_category):
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-05", amount=100, type="expense")

    response = client.get("/api/reports/by-category?month=3&year=2026", headers=auth_headers)
    body = response.json()
    ids = {c["category_id"] for c in body}
    assert groceries_category["id"] in ids
    assert rent_category["id"] not in ids


def test_by_category_excludes_income(client, auth_headers, account, income_category, groceries_category):
    make_transaction(client, auth_headers, account["id"], income_category["id"], date="2026-03-05", amount=1000, type="income")
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-06", amount=80, type="expense")

    response = client.get("/api/reports/by-category?month=3&year=2026", headers=auth_headers)
    body = response.json()
    assert len(body) == 1
    assert body[0]["category_id"] == groceries_category["id"]


def test_by_category_uncategorized_bucket(client, auth_headers, account, groceries_category):
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-05", amount=100, type="expense")
    make_transaction(client, auth_headers, account["id"], None, date="2026-03-06", amount=40, type="expense")
    make_transaction(client, auth_headers, account["id"], None, date="2026-03-07", amount=10, type="expense")

    response = client.get("/api/reports/by-category?month=3&year=2026", headers=auth_headers)
    body = response.json()
    uncategorized = [c for c in body if c["category_id"] is None]
    assert len(uncategorized) == 1
    assert uncategorized[0]["name"] == "Sem categoria"
    assert uncategorized[0]["color"] == "#9e9e9e"
    assert uncategorized[0]["total"] == 50.0


def test_by_category_no_uncategorized_bucket_when_none(client, auth_headers, account, groceries_category):
    make_transaction(client, auth_headers, account["id"], groceries_category["id"], date="2026-03-05", amount=100, type="expense")

    response = client.get("/api/reports/by-category?month=3&year=2026", headers=auth_headers)
    body = response.json()
    assert all(c["category_id"] is not None for c in body)


def test_by_category_empty_month(client, auth_headers):
    response = client.get("/api/reports/by-category?month=6&year=2026", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_by_category_requires_auth(client):
    response = client.get("/api/reports/by-category?month=3&year=2026")
    assert response.status_code == 401
