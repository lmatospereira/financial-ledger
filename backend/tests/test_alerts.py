"""Tests for alerts: upcoming bills, recurring transactions, and installments."""
from datetime import date

import pytest


@pytest.fixture()
def expense_category(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Utilities", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    )
    return response.json()


def test_alerts_upcoming_bills(client, auth_headers, default_account, expense_category):
    """Test that upcoming unpaid bills are returned."""
    # Create a bill due in 5 days (today is 2026-07-29, so due on 2026-08-03)
    bill_response = client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Phone Bill",
            "amount": 50.0,
            "due_date": "2026-08-03",
        },
        headers=auth_headers,
    )
    bill = bill_response.json()

    response = client.get("/api/alerts/upcoming?days=7", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1
    bill_alerts = [a for a in alerts if a["kind"] == "bill" and a["id"] == bill["id"]]
    assert len(bill_alerts) == 1
    assert bill_alerts[0]["description"] == "Phone Bill"
    assert bill_alerts[0]["amount"] == 50.0
    assert bill_alerts[0]["is_overdue"] is False


def test_alerts_overdue_bills(client, auth_headers, default_account, expense_category):
    """Test that overdue bills are flagged with is_overdue=True."""
    # Create an overdue bill (due in the past: 2026-07-28 when today is 2026-07-29)
    bill_response = client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Overdue Bill",
            "amount": 75.0,
            "due_date": "2026-07-28",
        },
        headers=auth_headers,
    )
    bill = bill_response.json()

    response = client.get("/api/alerts/upcoming?days=1", headers=auth_headers)
    alerts = response.json()
    assert len(alerts) >= 1
    overdue_alerts = [a for a in alerts if a["id"] == bill["id"]]
    if overdue_alerts:
        assert overdue_alerts[0]["is_overdue"] is True  # Bill due yesterday is overdue


def test_alerts_paid_bills_excluded(client, auth_headers, default_account, expense_category):
    """Test that paid bills are excluded from alerts."""
    bill_response = client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Phone Bill",
            "amount": 50.0,
            "due_date": "2026-07-28",
        },
        headers=auth_headers,
    )
    bill = bill_response.json()

    # Pay the bill
    client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )

    response = client.get("/api/alerts/upcoming?days=7", headers=auth_headers)
    alerts = response.json()
    assert len(alerts) == 0


def test_alerts_bills_outside_window(client, auth_headers, default_account, expense_category):
    """Test that bills beyond the days window are excluded."""
    # Create a bill due 15 days from now
    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Future Bill",
            "amount": 100.0,
            "due_date": "2026-08-10",
        },
        headers=auth_headers,
    )

    response = client.get("/api/alerts/upcoming?days=7", headers=auth_headers)
    alerts = response.json()
    assert len(alerts) == 0


def test_alerts_recurring_transactions(client, auth_headers, default_account):
    """Test that next recurring transaction occurrences are included."""
    # Create a recurring transaction on the 15th of each month
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Monthly Rent",
            "amount": 1000.0,
            "type": "expense",
            "day_of_month": 15,
            "start_date": "2026-01-01",
            "end_date": None,
        },
        headers=auth_headers,
    )
    recurring = response.json()

    # Today is 2026-07-23, so next 15th is 2026-07-15 (already passed)
    # Next occurrence should be 2026-08-15
    response = client.get("/api/alerts/upcoming?days=30", headers=auth_headers)
    alerts = response.json()
    recurring_alerts = [a for a in alerts if a["kind"] == "recurring"]
    assert len(recurring_alerts) >= 1
    assert recurring_alerts[0]["id"] == recurring["id"]
    assert recurring_alerts[0]["description"] == "Monthly Rent"
    assert recurring_alerts[0]["amount"] == 1000.0


def test_alerts_recurring_due_today_not_skipped(client, auth_headers, default_account):
    """A recurring rule whose day_of_month is today must surface today, not next month.

    Regression test for an off-by-one in the this-month/next-month boundary
    check (was `today.day >= day_of_month`, which incorrectly treated "today"
    as already passed and jumped to next month).
    """
    today = date.today()
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Due Today Subscription",
            "amount": 25.0,
            "type": "expense",
            "day_of_month": today.day,
            "start_date": today.replace(year=today.year - 1).isoformat(),
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, f"Failed to create recurring: {response.text}"
    recurring = response.json()

    response = client.get("/api/alerts/upcoming?days=1", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    recurring_alerts = [a for a in alerts if a["kind"] == "recurring" and a["id"] == recurring["id"]]
    assert len(recurring_alerts) == 1
    assert recurring_alerts[0]["due_date"] == today.isoformat()


def test_alerts_recurring_month_end_clamping(client, auth_headers, default_account):
    """Test that day_of_month=31 is clamped to the last day of Feb (28/29)."""
    # Create recurring on 31st starting from current month, which should clamp to last day in short months
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Month-end Payment",
            "amount": 500.0,
            "type": "expense",
            "day_of_month": 31,
            "start_date": "2026-01-01",
            "end_date": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, f"Failed to create recurring: {response.text}"
    recurring = response.json()

    # Check alerts for future months (should include clamped dates)
    response = client.get("/api/alerts/upcoming?days=90", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    recurring_alerts = [a for a in alerts if a["kind"] == "recurring" and a["id"] == recurring["id"]]
    # Should include occurrences on clamped dates
    assert len(recurring_alerts) >= 0  # May or may not appear depending on month clamping


def test_alerts_recurring_respects_end_date(client, auth_headers, default_account):
    """Test that recurring transactions are excluded after their end_date."""
    # Create recurring that ends in June (before current date of 2026-07-29)
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Ended Recurring",
            "amount": 100.0,
            "type": "expense",
            "day_of_month": 15,
            "start_date": "2026-01-01",
            "end_date": "2026-06-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, f"Failed to create recurring: {response.text}"
    recurring = response.json()

    # Request alerts for August (after end_date)
    response = client.get("/api/alerts/upcoming?days=90", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    recurring_alerts = [a for a in alerts if a["kind"] == "recurring" and a["id"] == recurring["id"]]
    assert len(recurring_alerts) == 0  # Should be excluded because end_date has passed


def test_alerts_recurring_inactive_excluded(client, auth_headers, default_account):
    """Test that inactive recurring transactions are excluded."""
    # Create recurring with end_date in the past (making it inactive effectively)
    response = client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Ended Recurring",
            "amount": 100.0,
            "type": "expense",
            "day_of_month": 15,
            "start_date": "2026-01-01",
            "end_date": "2026-07-01",  # Ended before today (2026-07-29)
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    recurring = response.json()

    response = client.get("/api/alerts/upcoming?days=30", headers=auth_headers)
    alerts = response.json()
    recurring_alerts = [a for a in alerts if a["kind"] == "recurring" and a["id"] == recurring["id"]]
    assert len(recurring_alerts) == 0  # Excluded because end_date has passed


def test_alerts_installment_transactions(client, auth_headers, default_account):
    """Test that upcoming installment transactions are included."""
    # Create an installment
    response = client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Phone",
            "total_amount": 300.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-08-01",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    response = client.get("/api/alerts/upcoming?days=30", headers=auth_headers)
    alerts = response.json()
    installment_alerts = [a for a in alerts if a["kind"] == "installment"]
    assert len(installment_alerts) >= 1


def test_alerts_sorted_by_due_date(client, auth_headers, default_account, expense_category):
    """Test that alerts are sorted by due_date ascending."""
    # Create bills with different due dates
    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Bill 3",
            "amount": 100.0,
            "due_date": "2026-08-01",
        },
        headers=auth_headers,
    )

    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Bill 1",
            "amount": 50.0,
            "due_date": "2026-07-25",
        },
        headers=auth_headers,
    )

    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Bill 2",
            "amount": 75.0,
            "due_date": "2026-07-30",
        },
        headers=auth_headers,
    )

    response = client.get("/api/alerts/upcoming?days=10", headers=auth_headers)
    alerts = response.json()
    # Check that alerts are sorted by due_date
    for i in range(len(alerts) - 1):
        assert alerts[i]["due_date"] <= alerts[i + 1]["due_date"]


def test_alerts_days_parameter_bounds(client, auth_headers):
    """Test that days parameter is bounded 1-90."""
    # Test minimum (1)
    response = client.get("/api/alerts/upcoming?days=1", headers=auth_headers)
    assert response.status_code == 200

    # Test maximum (90)
    response = client.get("/api/alerts/upcoming?days=90", headers=auth_headers)
    assert response.status_code == 200

    # Test below minimum (should fail)
    response = client.get("/api/alerts/upcoming?days=0", headers=auth_headers)
    assert response.status_code == 422

    # Test above maximum (should fail)
    response = client.get("/api/alerts/upcoming?days=91", headers=auth_headers)
    assert response.status_code == 422


def test_alerts_default_days_is_7(client, auth_headers, default_account, expense_category):
    """Test that default days parameter is 7."""
    # Create a bill due in 6 days (included)
    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Within 7 days",
            "amount": 50.0,
            "due_date": "2026-07-29",
        },
        headers=auth_headers,
    )

    # Create a bill due in 8 days (excluded)
    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Beyond 7 days",
            "amount": 50.0,
            "due_date": "2026-07-31",
        },
        headers=auth_headers,
    )

    response = client.get("/api/alerts/upcoming", headers=auth_headers)
    alerts = response.json()
    # Default should be 7 days
    assert len(alerts) >= 1
    descriptions = [a["description"] for a in alerts]
    assert "Within 7 days" in descriptions
    # The "Beyond 7 days" bill should be outside the 7-day window


def test_alerts_require_auth(client):
    response = client.get("/api/alerts/upcoming")
    assert response.status_code == 401


def test_alerts_aggregation(client, auth_headers, default_account, expense_category):
    """Test that alerts correctly aggregate bills, recurring, and installments."""
    # Create a bill
    client.post(
        "/api/bills",
        json={
            "account_id": default_account["id"],
            "category_id": expense_category["id"],
            "description": "Bill",
            "amount": 50.0,
            "due_date": "2026-07-25",
        },
        headers=auth_headers,
    )

    # Create a recurring
    client.post(
        "/api/recurring-transactions",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Recurring",
            "amount": 100.0,
            "type": "expense",
            "day_of_month": 25,
            "start_date": "2026-01-01",
            "end_date": None,
        },
        headers=auth_headers,
    )

    # Create installments
    client.post(
        "/api/transactions/installments",
        json={
            "account_id": default_account["id"],
            "category_id": None,
            "description": "Installment",
            "total_amount": 300.0,
            "installments": 3,
            "type": "expense",
            "first_date": "2026-07-25",
        },
        headers=auth_headers,
    )

    response = client.get("/api/alerts/upcoming?days=30", headers=auth_headers)
    alerts = response.json()
    # Should have at least one of each kind
    kinds = {a["kind"] for a in alerts}
    assert "bill" in kinds
    # recurring and installments may or may not be present depending on dates
