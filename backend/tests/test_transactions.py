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


def make_transaction(client, auth_headers, category_id, **overrides):
    payload = {
        "date": "2026-03-15",
        "description": "Test transaction",
        "amount": 100.0,
        "type": "income",
        "category_id": category_id,
    }
    payload.update(overrides)
    return client.post("/api/transactions", json=payload, headers=auth_headers)


def test_create_transaction(client, auth_headers, income_category):
    response = make_transaction(client, auth_headers, income_category["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 100.0
    assert body["category_id"] == income_category["id"]
    assert "created_at" in body


def test_create_transaction_unknown_category(client, auth_headers):
    response = make_transaction(client, auth_headers, 999)
    assert response.status_code == 404


def test_create_transaction_without_category(client, auth_headers):
    response = make_transaction(client, auth_headers, None)
    assert response.status_code == 201
    body = response.json()
    assert body["category_id"] is None
    assert body["category"] is None


def test_update_transaction_remove_category(client, auth_headers, income_category):
    created = make_transaction(client, auth_headers, income_category["id"]).json()
    response = client.put(
        f"/api/transactions/{created['id']}",
        json={
            "date": "2026-03-16",
            "description": "Updated",
            "amount": 50.0,
            "type": "expense",
            "category_id": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] is None
    assert body["category"] is None


def test_create_transaction_negative_amount_rejected(client, auth_headers, income_category):
    response = make_transaction(client, auth_headers, income_category["id"], amount=-5)
    assert response.status_code == 422


def test_list_transactions_filtered_by_month(client, auth_headers, income_category):
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-15")
    make_transaction(client, auth_headers, income_category["id"], date="2026-04-01")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["date"] == "2026-03-15"


def test_list_transactions_sorted_by_date(client, auth_headers, income_category):
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-20")
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-05")
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-10")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    dates = [t["date"] for t in response.json()]
    assert dates == sorted(dates)


def test_update_transaction(client, auth_headers, income_category, expense_category):
    created = make_transaction(client, auth_headers, income_category["id"]).json()
    response = client.put(
        f"/api/transactions/{created['id']}",
        json={
            "date": "2026-03-16",
            "description": "Updated",
            "amount": 50.0,
            "type": "expense",
            "category_id": expense_category["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Updated"
    assert body["amount"] == 50.0
    assert body["type"] == "expense"


def test_update_transaction_not_found(client, auth_headers, income_category):
    response = client.put(
        "/api/transactions/999",
        json={
            "date": "2026-03-16",
            "description": "Updated",
            "amount": 50.0,
            "type": "income",
            "category_id": income_category["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_transaction(client, auth_headers, income_category):
    created = make_transaction(client, auth_headers, income_category["id"]).json()
    response = client.delete(f"/api/transactions/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.json() == []


def test_delete_transaction_not_found(client, auth_headers):
    response = client.delete("/api/transactions/999", headers=auth_headers)
    assert response.status_code == 404


def test_transactions_require_auth(client):
    response = client.get("/api/transactions?month=3&year=2026")
    assert response.status_code == 401


def test_list_transactions_includes_category_object(client, auth_headers, income_category):
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-15")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["category"] == income_category


def test_list_transactions_mixed_categorized_and_uncategorized(client, auth_headers, income_category):
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-05")
    make_transaction(client, auth_headers, None, date="2026-03-10")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    by_date = {t["date"]: t for t in results}
    assert by_date["2026-03-05"]["category"] == income_category
    assert by_date["2026-03-10"]["category"] is None
    assert by_date["2026-03-10"]["category_id"] is None


def test_list_transactions_missing_query_param_returns_string_detail(client, auth_headers):
    response = client.get("/api/transactions?month=3", headers=auth_headers)
    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["detail"]


# ---------- Summary edge cases ----------
def test_summary_empty_month(client, auth_headers):
    response = client.get("/api/summary?month=6&year=2026", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "income_total": 0.0,
        "expense_total": 0.0,
        "balance": 0.0,
        "previous_balance": 0.0,
    }


def test_summary_income_only_month(client, auth_headers, income_category):
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-05", amount=200)
    make_transaction(client, auth_headers, income_category["id"], date="2026-03-20", amount=300)

    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    body = response.json()
    assert body["income_total"] == 500.0
    assert body["expense_total"] == 0.0
    assert body["balance"] == 500.0
    assert body["previous_balance"] == 0.0


def test_summary_month_rollover(client, auth_headers, income_category, expense_category):
    # March: income 500, expense 200 -> balance 300
    make_transaction(
        client, auth_headers, income_category["id"], date="2026-03-05", amount=500, type="income"
    )
    make_transaction(
        client,
        auth_headers,
        expense_category["id"],
        date="2026-03-10",
        amount=200,
        type="expense",
    )

    march_summary = client.get("/api/summary?month=3&year=2026", headers=auth_headers).json()
    assert march_summary["balance"] == 300.0
    assert march_summary["previous_balance"] == 0.0

    # April: income 100 only, but previous_balance should carry March's 300
    make_transaction(
        client, auth_headers, income_category["id"], date="2026-04-05", amount=100, type="income"
    )

    april_summary = client.get("/api/summary?month=4&year=2026", headers=auth_headers).json()
    assert april_summary["income_total"] == 100.0
    assert april_summary["expense_total"] == 0.0
    assert april_summary["balance"] == 100.0
    assert april_summary["previous_balance"] == 300.0


def test_summary_year_rollover(client, auth_headers, income_category):
    make_transaction(
        client, auth_headers, income_category["id"], date="2025-12-15", amount=1000, type="income"
    )

    response = client.get("/api/summary?month=1&year=2026", headers=auth_headers)
    body = response.json()
    assert body["previous_balance"] == 1000.0
    assert body["income_total"] == 0.0


def test_summary_with_uncategorized_transactions(client, auth_headers, income_category, expense_category):
    # Mix of categorized and uncategorized transactions; category should not
    # affect the income/expense totals at all.
    make_transaction(
        client, auth_headers, income_category["id"], date="2026-03-05", amount=200, type="income"
    )
    make_transaction(client, auth_headers, None, date="2026-03-06", amount=150, type="income")
    make_transaction(
        client, auth_headers, expense_category["id"], date="2026-03-07", amount=50, type="expense"
    )
    make_transaction(client, auth_headers, None, date="2026-03-08", amount=30, type="expense")

    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["income_total"] == 350.0
    assert body["expense_total"] == 80.0
    assert body["balance"] == 270.0
    assert body["previous_balance"] == 0.0


def test_summary_requires_auth(client):
    response = client.get("/api/summary?month=3&year=2026")
    assert response.status_code == 401
