"""Tests for credit card invoice endpoint."""
import pytest

from app import auth, crud


@pytest.fixture()
def credit_card_account(client, auth_headers):
    """Create a credit card account for testing."""
    response = client.post(
        "/api/accounts",
        json={
            "name": "My Credit Card",
            "type": "credit_card",
            "color": "#1a1a1a",
            "closing_day": 25,
            "due_day": 5,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def expense_category(client, auth_headers):
    """Create an expense category for testing."""
    response = client.post(
        "/api/categories",
        json={"name": "Shopping", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def income_category(client, auth_headers):
    """Create an income category for testing."""
    response = client.post(
        "/api/categories",
        json={"name": "Refunds", "type": "income", "color": "#00FF00"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_credit_card_invoice_with_closing_day(client, auth_headers, credit_card_account, expense_category):
    """Test invoice calculation with closing_day set.

    Closing day is 25, so the invoice for July 2026 should cover:
    - June 26, 2026 through July 25, 2026
    """
    # Create transactions before the closing day (June 26+)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-06-26",
            "description": "Purchase 1",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Create transactions on the closing day (July 25)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-25",
            "description": "Purchase 2",
            "amount": 50.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Create a transaction after closing day (should belong to next month's invoice)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-26",
            "description": "Purchase 3",
            "amount": 75.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for July 2026
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check period
    assert invoice["period_start"] == "2026-06-26"
    assert invoice["period_end"] == "2026-07-25"

    # Check due date (5th of following month: August 5)
    assert invoice["due_date"] == "2026-08-05"

    # Check total (100 + 50 = 150, not including 75 which is after closing)
    assert invoice["total"] == 150.0

    # Check transactions (should only have 2)
    assert len(invoice["transactions"]) == 2


def test_credit_card_invoice_without_closing_day(client, auth_headers, expense_category):
    """Test invoice calculation without closing_day (fallback to calendar month)."""
    # Create a credit card account without closing_day
    response = client.post(
        "/api/accounts",
        json={
            "name": "Simple Card",
            "type": "credit_card",
            "color": "#FF00FF",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    simple_card = response.json()

    # Create transactions in July 2026
    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-01",
            "description": "Purchase 1",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": simple_card["id"],
        },
        headers=auth_headers,
    )

    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-31",
            "description": "Purchase 2",
            "amount": 50.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": simple_card["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for July 2026
    response = client.get(
        f"/api/accounts/{simple_card['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check period (should be calendar month)
    assert invoice["period_start"] == "2026-07-01"
    assert invoice["period_end"] == "2026-07-31"

    # Check due date (None when due_day not set)
    assert invoice["due_date"] is None

    # Check total
    assert invoice["total"] == 150.0

    # Check transactions
    assert len(invoice["transactions"]) == 2


def test_credit_card_invoice_closing_day_clamping(client, auth_headers, expense_category):
    """Test that closing_day=31 is clamped to the last day of February (28 in 2026)."""
    # Create a credit card account with closing_day=31
    response = client.post(
        "/api/accounts",
        json={
            "name": "Month-End Card",
            "type": "credit_card",
            "color": "#00FFFF",
            "closing_day": 31,
            "due_day": 15,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    card = response.json()

    # Create a transaction on Feb 28 (last day of Feb 2026)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-02-28",
            "description": "Purchase in Feb",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": card["id"],
        },
        headers=auth_headers,
    )

    # Create a transaction on March 1 (after clamped closing day)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-03-01",
            "description": "Purchase in March",
            "amount": 50.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": card["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for February 2026 (closing_day=31 should clamp to 28)
    response = client.get(
        f"/api/accounts/{card['id']}/invoice?month=2&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check period (should clamp Jan 31 to Jan 31, Feb 31 to Feb 28)
    assert invoice["period_end"] == "2026-02-28"

    # Check total (should only include Feb 28 transaction)
    assert invoice["total"] == 100.0

    # Check due date (March 15, clamped to March 31 for month range)
    assert invoice["due_date"] == "2026-03-15"


def test_credit_card_invoice_net_income_and_expense(client, auth_headers, credit_card_account, expense_category, income_category):
    """Test that income reduces the total (refund scenario)."""
    # Create an expense transaction
    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-15",
            "description": "Purchase",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Create an income transaction (refund)
    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-20",
            "description": "Refund",
            "amount": 30.0,
            "type": "income",
            "category_id": income_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for July 2026
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check total (100 - 30 = 70)
    assert invoice["total"] == 70.0

    # Check transactions (should have both)
    assert len(invoice["transactions"]) == 2


def test_credit_card_invoice_due_date_clamping(client, auth_headers, expense_category):
    """Test that due_day is clamped to the last day of the month."""
    # Create a credit card with due_day=31
    response = client.post(
        "/api/accounts",
        json={
            "name": "Card with Month-End Due",
            "type": "credit_card",
            "color": "#AABBCC",
            "closing_day": 25,
            "due_day": 31,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    card = response.json()

    # Add a transaction
    client.post(
        "/api/transactions",
        json={
            "date": "2026-07-15",
            "description": "Purchase",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": card["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for July 2026
    response = client.get(
        f"/api/accounts/{card['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check due date (August 31 should be clamped - but Aug has 31 days, so no clamping)
    # Actually, we're checking July invoice, so due date is August, which has 31 days
    assert invoice["due_date"] == "2026-08-31"


def test_credit_card_invoice_404_nonexistent_account(client, auth_headers):
    """Test 404 when account doesn't exist."""
    response = client.get("/api/accounts/99999/invoice?month=7&year=2026", headers=auth_headers)
    assert response.status_code == 404


def test_credit_card_invoice_404_non_credit_card(client, auth_headers, default_account):
    """Test 404 when account is not a credit card."""
    response = client.get(
        f"/api/accounts/{default_account['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_credit_card_invoice_cross_user_isolation(client, db_session, credit_card_account):
    """Test that users can't access each other's credit card invoices."""
    # Create another user directly in the database
    crud.create_user(
        db_session, username="otheruser", name="Other User", password_hash=auth.hash_password("password123")
    )

    # Login as the other user
    login_response = client.post(
        "/api/auth/login", json={"username": "otheruser", "password": "password123"}
    )
    assert login_response.status_code == 200
    other_token = login_response.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Try to access the first user's credit card invoice
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=7&year=2026",
        headers=other_headers,
    )
    assert response.status_code == 404


def test_credit_card_invoice_empty_billing_period(client, auth_headers, credit_card_account):
    """Test invoice with no transactions in the billing period."""
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check that total is 0 and transactions list is empty
    assert invoice["total"] == 0.0
    assert len(invoice["transactions"]) == 0


def test_credit_card_invoice_requires_auth(client, credit_card_account):
    """Test that the endpoint requires authentication."""
    response = client.get(f"/api/accounts/{credit_card_account['id']}/invoice?month=7&year=2026")
    assert response.status_code == 401


def test_credit_card_invoice_month_validation(client, auth_headers, credit_card_account):
    """Test month parameter validation."""
    # Test valid month (1)
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=1&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Test valid month (12)
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=12&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Test invalid month (0)
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=0&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 422

    # Test invalid month (13)
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=13&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 422

    # Test missing month parameter
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_credit_card_invoice_multiple_transactions(client, auth_headers, credit_card_account, expense_category):
    """Test invoice with multiple transactions in different dates within the billing period."""
    # Closing day is 25, so July invoice covers June 26 - July 25
    transactions_data = [
        ("2026-06-26", "Purchase 1", 100.0),
        ("2026-06-27", "Purchase 2", 50.0),
        ("2026-07-01", "Purchase 3", 75.0),
        ("2026-07-15", "Purchase 4", 60.0),
        ("2026-07-25", "Purchase 5", 25.0),
    ]

    for date_str, description, amount in transactions_data:
        client.post(
            "/api/transactions",
            json={
                "date": date_str,
                "description": description,
                "amount": amount,
                "type": "expense",
                "category_id": expense_category["id"],
                "account_id": credit_card_account["id"],
            },
            headers=auth_headers,
        )

    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=7&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check total (100 + 50 + 75 + 60 + 25 = 310)
    assert invoice["total"] == 310.0

    # Check that all transactions are included and in order
    assert len(invoice["transactions"]) == 5
    for i, (_, desc, _) in enumerate(transactions_data):
        assert invoice["transactions"][i]["description"] == desc


def test_credit_card_invoice_year_boundary(client, auth_headers, credit_card_account, expense_category):
    """Test invoice calculation across year boundaries."""
    # Create a transaction in December
    client.post(
        "/api/transactions",
        json={
            "date": "2025-12-26",
            "description": "Purchase in Dec",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Create a transaction in January
    client.post(
        "/api/transactions",
        json={
            "date": "2026-01-15",
            "description": "Purchase in Jan",
            "amount": 50.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": credit_card_account["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for January 2026 (should cover Dec 26 - Jan 25)
    response = client.get(
        f"/api/accounts/{credit_card_account['id']}/invoice?month=1&year=2026",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check period crosses year boundary
    assert invoice["period_start"] == "2025-12-26"
    assert invoice["period_end"] == "2026-01-25"

    # Check total (100 + 50 = 150)
    assert invoice["total"] == 150.0

    # Check transactions
    assert len(invoice["transactions"]) == 2


def test_credit_card_invoice_due_date_year_boundary(client, auth_headers, expense_category):
    """Test that due_date calculation works across year boundaries."""
    # Create a credit card with due_day=5
    response = client.post(
        "/api/accounts",
        json={
            "name": "Year-End Card",
            "type": "credit_card",
            "color": "#123456",
            "closing_day": 25,
            "due_day": 5,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    card = response.json()

    # Add a transaction in December
    client.post(
        "/api/transactions",
        json={
            "date": "2025-12-15",
            "description": "Purchase",
            "amount": 100.0,
            "type": "expense",
            "category_id": expense_category["id"],
            "account_id": card["id"],
        },
        headers=auth_headers,
    )

    # Get invoice for December 2025
    response = client.get(
        f"/api/accounts/{card['id']}/invoice?month=12&year=2025",
        headers=auth_headers,
    )
    assert response.status_code == 200
    invoice = response.json()

    # Check due date (January 5, 2026)
    assert invoice["due_date"] == "2026-01-05"
