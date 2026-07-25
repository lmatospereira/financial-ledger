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


def test_create_transaction(client, auth_headers, income_category, default_account):
    response = make_transaction(client, auth_headers, income_category["id"], default_account["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 100.0
    assert body["category_id"] == income_category["id"]
    assert body["account_id"] == default_account["id"]
    assert "created_at" in body


def test_create_transaction_unknown_category(client, auth_headers, default_account):
    response = make_transaction(client, auth_headers, 999, default_account["id"])
    assert response.status_code == 404


def test_create_transaction_unknown_account(client, auth_headers, income_category):
    response = make_transaction(client, auth_headers, income_category["id"], 999)
    assert response.status_code == 404


def test_create_transaction_without_category(client, auth_headers, default_account):
    response = make_transaction(client, auth_headers, None, default_account["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["category_id"] is None
    assert body["category"] is None


def test_create_transaction_type_transfer_rejected(client, auth_headers, default_account):
    response = make_transaction(
        client, auth_headers, None, default_account["id"], type="transfer"
    )
    assert response.status_code == 422


def test_update_transaction_remove_category(client, auth_headers, income_category, default_account):
    created = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"]
    ).json()
    response = client.put(
        f"/api/transactions/{created['id']}",
        json={
            "date": "2026-03-16",
            "description": "Updated",
            "amount": 50.0,
            "type": "expense",
            "category_id": None,
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] is None
    assert body["category"] is None


def test_create_transaction_negative_amount_rejected(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=-5
    )
    assert response.status_code == 422


def test_list_transactions_filtered_by_month(client, auth_headers, income_category, default_account):
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-15")
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-04-01")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["date"] == "2026-03-15"


def test_list_transactions_sorted_by_date(client, auth_headers, income_category, default_account):
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-20")
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-05")
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-10")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    dates = [t["date"] for t in response.json()]
    assert dates == sorted(dates)


def test_update_transaction(client, auth_headers, income_category, expense_category, default_account):
    created = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"]
    ).json()
    response = client.put(
        f"/api/transactions/{created['id']}",
        json={
            "date": "2026-03-16",
            "description": "Updated",
            "amount": 50.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Updated"
    assert body["amount"] == 50.0
    assert body["type"] == "expense"


def test_update_transaction_not_found(client, auth_headers, income_category, default_account):
    response = client.put(
        "/api/transactions/999",
        json={
            "date": "2026-03-16",
            "description": "Updated",
            "amount": 50.0,
            "type": "income",
            "category_id": income_category["id"],
            "account_id": default_account["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_transaction(client, auth_headers, income_category, default_account):
    created = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"]
    ).json()
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


def test_list_transactions_includes_category_object(client, auth_headers, income_category, default_account):
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-15")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["category"] == income_category


def test_list_transactions_includes_account_object(client, auth_headers, income_category, default_account):
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-15")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    account = results[0]["account"]
    assert account["id"] == default_account["id"]
    assert account["name"] == default_account["name"]
    # AccountRef is deliberately lighter than AccountOut: no balance/created_at.
    assert "balance" not in account
    assert "created_at" not in account


def test_list_transactions_mixed_categorized_and_uncategorized(client, auth_headers, income_category, default_account):
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-05")
    make_transaction(client, auth_headers, None, default_account["id"], date="2026-03-10")

    response = client.get("/api/transactions?month=3&year=2026", headers=auth_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    by_date = {t["date"]: t for t in results}
    assert by_date["2026-03-05"]["category"] == income_category
    assert by_date["2026-03-10"]["category"] is None
    assert by_date["2026-03-10"]["category_id"] is None


def test_list_transactions_filtered_by_account(client, auth_headers, income_category, default_account):
    other_account = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#654321"},
        headers=auth_headers,
    ).json()
    make_transaction(client, auth_headers, income_category["id"], default_account["id"], date="2026-03-05")
    make_transaction(client, auth_headers, income_category["id"], other_account["id"], date="2026-03-06")

    response = client.get(
        f"/api/transactions?month=3&year=2026&account_id={default_account['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["account_id"] == default_account["id"]


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


def test_summary_income_only_month(client, auth_headers, income_category, default_account):
    make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-05", amount=200
    )
    make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2026-03-20", amount=300
    )

    response = client.get("/api/summary?month=3&year=2026", headers=auth_headers)
    body = response.json()
    assert body["income_total"] == 500.0
    assert body["expense_total"] == 0.0
    assert body["balance"] == 500.0
    assert body["previous_balance"] == 0.0


def test_summary_month_rollover(client, auth_headers, income_category, expense_category, default_account):
    # March: income 500, expense 200 -> balance 300
    make_transaction(
        client,
        auth_headers,
        income_category["id"],
        default_account["id"],
        date="2026-03-05",
        amount=500,
        type="income",
    )
    make_transaction(
        client,
        auth_headers,
        expense_category["id"],
        default_account["id"],
        date="2026-03-10",
        amount=200,
        type="expense",
    )

    march_summary = client.get("/api/summary?month=3&year=2026", headers=auth_headers).json()
    assert march_summary["balance"] == 300.0
    assert march_summary["previous_balance"] == 0.0

    # April: income 100 only, but previous_balance should carry March's 300
    make_transaction(
        client,
        auth_headers,
        income_category["id"],
        default_account["id"],
        date="2026-04-05",
        amount=100,
        type="income",
    )

    april_summary = client.get("/api/summary?month=4&year=2026", headers=auth_headers).json()
    assert april_summary["income_total"] == 100.0
    assert april_summary["expense_total"] == 0.0
    assert april_summary["balance"] == 100.0
    assert april_summary["previous_balance"] == 300.0


def test_summary_year_rollover(client, auth_headers, income_category, default_account):
    make_transaction(
        client,
        auth_headers,
        income_category["id"],
        default_account["id"],
        date="2025-12-15",
        amount=1000,
        type="income",
    )

    response = client.get("/api/summary?month=1&year=2026", headers=auth_headers)
    body = response.json()
    assert body["previous_balance"] == 1000.0
    assert body["income_total"] == 0.0


def test_summary_with_uncategorized_transactions(
    client, auth_headers, income_category, expense_category, default_account
):
    # Mix of categorized and uncategorized transactions; category should not
    # affect the income/expense totals at all.
    make_transaction(
        client,
        auth_headers,
        income_category["id"],
        default_account["id"],
        date="2026-03-05",
        amount=200,
        type="income",
    )
    make_transaction(
        client, auth_headers, None, default_account["id"], date="2026-03-06", amount=150, type="income"
    )
    make_transaction(
        client,
        auth_headers,
        expense_category["id"],
        default_account["id"],
        date="2026-03-07",
        amount=50,
        type="expense",
    )
    make_transaction(
        client, auth_headers, None, default_account["id"], date="2026-03-08", amount=30, type="expense"
    )

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


# ---------- Guardrails: Amount limits ----------
def test_create_transaction_amount_above_max_rejected(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=1_000_000_000.0
    )
    assert response.status_code == 422


def test_create_transaction_amount_at_max_accepted(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], amount=999_999_999.99
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 999_999_999.99


def test_create_transfer_amount_above_max_rejected(client, auth_headers, default_account):
    other_account = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#654321"},
        headers=auth_headers,
    ).json()
    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": default_account["id"],
            "to_account_id": other_account["id"],
            "amount": 1_000_000_000.0,
            "date": "2026-03-15",
            "description": "Big transfer",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_transfer_amount_at_max_accepted(client, auth_headers, default_account):
    other_account = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#654321"},
        headers=auth_headers,
    ).json()
    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": default_account["id"],
            "to_account_id": other_account["id"],
            "amount": 999_999_999.99,
            "date": "2026-03-15",
            "description": "Max transfer",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 999_999_999.99


def test_create_budget_amount_above_max_rejected(client, auth_headers, expense_category):
    response = client.post(
        "/api/budgets",
        json={"category_id": expense_category["id"], "amount": 1_000_000_000.0},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_budget_amount_at_max_accepted(client, auth_headers, expense_category):
    response = client.post(
        "/api/budgets",
        json={"category_id": expense_category["id"], "amount": 999_999_999.99},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 999_999_999.99


def test_create_recurring_transaction_amount_above_max_rejected(client, auth_headers, income_category, default_account):
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Monthly salary",
            "amount": 1_000_000_000.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-03-15",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_recurring_transaction_amount_at_max_accepted(client, auth_headers, income_category, default_account):
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Monthly salary",
            "amount": 999_999_999.99,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-03-15",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 999_999_999.99


def test_create_bill_amount_above_max_rejected(client, auth_headers):
    response = client.post(
        "/api/bills",
        json={
            "account_id": None,
            "category_id": None,
            "description": "Bill",
            "amount": 1_000_000_000.0,
            "due_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_bill_amount_at_max_accepted(client, auth_headers):
    response = client.post(
        "/api/bills",
        json={
            "account_id": None,
            "category_id": None,
            "description": "Bill",
            "amount": 999_999_999.99,
            "due_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 999_999_999.99


# ---------- Guardrails: Date range limits ----------
def test_create_transaction_date_far_future_rejected(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2029-07-26"
    )
    # Today is 2026-07-25, so 2029-07-26 is beyond the 3-year boundary
    assert response.status_code == 422


def test_create_transaction_date_far_past_rejected(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2023-07-24"
    )
    # Today is 2026-07-25, so 2023-07-24 is beyond the 3-year boundary in the past
    assert response.status_code == 422


def test_create_transaction_date_at_3_year_boundary_future_accepted(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2029-07-25"
    )
    # Today is 2026-07-25, so 2029-07-25 is exactly 3 years in the future
    # The guardrail is today.replace(year=today.year + 3), which is 2029-07-25
    # So this should be accepted
    assert response.status_code == 201


def test_create_transaction_date_at_3_year_boundary_past_accepted(client, auth_headers, income_category, default_account):
    response = make_transaction(
        client, auth_headers, income_category["id"], default_account["id"], date="2023-07-25"
    )
    # Today is 2026-07-25, so 2023-07-25 is exactly 3 years in the past
    # The guardrail is today.replace(year=today.year - 3), which is 2023-07-25
    # So this should be accepted
    assert response.status_code == 201


def test_create_transfer_date_far_future_rejected(client, auth_headers, default_account):
    other_account = client.post(
        "/api/accounts",
        json={"name": "Savings", "type": "savings", "color": "#654321"},
        headers=auth_headers,
    ).json()
    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": default_account["id"],
            "to_account_id": other_account["id"],
            "amount": 100.0,
            "date": "2030-01-01",
            "description": "Future transfer",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_bill_due_date_far_future_rejected(client, auth_headers):
    response = client.post(
        "/api/bills",
        json={
            "account_id": None,
            "category_id": None,
            "description": "Future bill",
            "amount": 100.0,
            "due_date": "2030-01-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_recurring_transaction_start_date_far_future_rejected(client, auth_headers, income_category, default_account):
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Future recurring",
            "amount": 100.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2030-01-01",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_recurring_transaction_end_date_far_future_rejected(client, auth_headers, income_category, default_account):
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Recurring with far future end",
            "amount": 100.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-03-15",
            "end_date": "2030-01-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_recurring_transaction_end_date_none_accepted(client, auth_headers, income_category, default_account):
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": income_category["id"],
            "description": "Open-ended recurring",
            "amount": 100.0,
            "type": "income",
            "day_of_month": 15,
            "start_date": "2026-03-15",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201


# ---------- Installments (parcelamento) ----------
def test_create_installments_3_count(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Laptop purchase",
            "total_amount": 300.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    transactions = response.json()
    assert len(transactions) == 3

    # Verify amounts: 100, 100, 100
    assert transactions[0]["amount"] == 100.0
    assert transactions[1]["amount"] == 100.0
    assert transactions[2]["amount"] == 100.0

    # Verify installment metadata
    assert transactions[0]["installment_number"] == 1
    assert transactions[0]["installment_total"] == 3
    assert transactions[1]["installment_number"] == 2
    assert transactions[2]["installment_number"] == 3

    # Verify all have the same group_id (not exposed in response, but check it's set)
    assert transactions[0]["account_id"] == default_account["id"]
    assert transactions[0]["category_id"] == expense_category["id"]
    assert transactions[0]["type"] == "expense"


def test_create_installments_3_with_rounding_remainder(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Test purchase",
            "total_amount": 100.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    transactions = response.json()
    assert len(transactions) == 3

    # 100 / 3 = 33.33, 33.33, 33.34 (last absorbs remainder)
    assert transactions[0]["amount"] == 33.33
    assert transactions[1]["amount"] == 33.33
    assert transactions[2]["amount"] == 33.34
    # Verify sum is exact
    total = sum(t["amount"] for t in transactions)
    assert total == 100.0


def test_create_installments_12_count(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Yearly plan",
            "total_amount": 1200.0,
            "installments": 12,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    transactions = response.json()
    assert len(transactions) == 12

    # Each should be 100.0
    for t in transactions:
        assert t["amount"] == 100.0

    # Verify dates advance by month
    assert transactions[0]["date"] == "2026-03-15"
    assert transactions[1]["date"] == "2026-04-15"
    assert transactions[11]["date"] == "2027-02-15"


def test_create_installments_420_count(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "35-year plan",
            "total_amount": 420000.0,
            "installments": 420,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    transactions = response.json()
    assert len(transactions) == 420

    # First installment
    assert transactions[0]["date"] == "2026-03-15"
    assert transactions[0]["installment_number"] == 1

    # Last installment should be ~35 years in the future (ignored by guardrail)
    last = transactions[419]
    assert last["installment_number"] == 420
    # 2026 + 35 = 2061, approximately (month arithmetic)
    assert last["date"].startswith("2061")


def test_create_installments_421_rejected(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Too many installments",
            "total_amount": 100.0,
            "installments": 421,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_installments_first_date_far_future_rejected(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Too far in future",
            "total_amount": 100.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2030-01-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_installments_first_date_far_past_rejected(client, auth_headers, expense_category, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Too far in past",
            "total_amount": 100.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2020-01-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_installments_month_clamping_feb(client, auth_headers, expense_category, default_account):
    """Test that day-of-month is clamped for short months (February)."""
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Feb test",
            "total_amount": 300.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-01-31",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    transactions = response.json()

    # 2026-01-31 (January, day 31)
    # 2026-02-28 (February, day clamped from 31 to 28)
    # 2026-03-31 (March, day 31)
    assert transactions[0]["date"] == "2026-01-31"
    assert transactions[1]["date"] == "2026-02-28"  # clamped
    assert transactions[2]["date"] == "2026-03-31"


def test_create_installments_unknown_account(client, auth_headers, expense_category):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": 999,
            "category_id": expense_category["id"],
            "description": "No such account",
            "total_amount": 100.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_installments_unknown_category(client, auth_headers, default_account):
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": 999,
            "description": "No such category",
            "total_amount": 100.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
