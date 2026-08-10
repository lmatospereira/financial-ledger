"""Tests for bills: CRUD operations, payment flow, and isolation."""
from datetime import date, timedelta

import pytest

from app import auth, crud, models


@pytest.fixture()
def expense_category(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Utilities", "type": "expense", "color": "#FF0000"},
        headers=auth_headers,
    )
    return response.json()


def make_bill(
    client,
    auth_headers,
    account_id=None,
    category_id=None,
    description="Phone Bill",
    amount=100.0,
    due_date="2026-03-15",
):
    payload = {
        "account_id": account_id,
        "category_id": category_id,
        "description": description,
        "amount": amount,
        "due_date": due_date,
    }
    return client.post("/api/bills", json=payload, headers=auth_headers)


def test_create_bill(client, auth_headers, expense_category):
    response = make_bill(
        client, auth_headers, category_id=expense_category["id"], amount=150.0
    )
    assert response.status_code == 201
    body = response.json()
    assert body["description"] == "Phone Bill"
    assert body["amount"] == 150.0
    assert body["category_id"] == expense_category["id"]
    assert body["paid"] is False
    assert body["paid_transaction_id"] is None
    assert "id" in body
    assert "created_at" in body


def test_create_bill_no_account_or_category(client, auth_headers):
    response = make_bill(client, auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["account_id"] is None
    assert body["category_id"] is None


def test_create_bill_invalid_account(client, auth_headers, expense_category):
    payload = {
        "account_id": 999,
        "category_id": expense_category["id"],
        "description": "Test Bill",
        "amount": 100.0,
        "due_date": "2026-03-15",
    }
    response = client.post("/api/bills", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_create_bill_invalid_category(client, auth_headers, default_account):
    payload = {
        "account_id": default_account["id"],
        "category_id": 999,
        "description": "Test Bill",
        "amount": 100.0,
        "due_date": "2026-03-15",
    }
    response = client.post("/api/bills", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_list_bills(client, auth_headers, expense_category):
    make_bill(client, auth_headers, category_id=expense_category["id"]).json()
    make_bill(
        client, auth_headers, category_id=expense_category["id"], due_date="2026-04-15"
    ).json()

    response = client.get("/api/bills", headers=auth_headers)
    assert response.status_code == 200
    bills = response.json()
    assert len(bills) == 2


def test_list_bills_filter_paid(client, auth_headers, default_account, expense_category):
    # Create 2 bills
    bill1 = make_bill(client, auth_headers, category_id=expense_category["id"]).json()
    bill2 = make_bill(
        client, auth_headers, category_id=expense_category["id"], due_date="2026-04-15"
    ).json()

    # Pay the first bill
    client.post(
        f"/api/bills/{bill1['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )

    # Filter unpaid
    response = client.get("/api/bills?paid=false", headers=auth_headers)
    bills = response.json()
    assert len(bills) == 1
    assert bills[0]["id"] == bill2["id"]

    # Filter paid
    response = client.get("/api/bills?paid=true", headers=auth_headers)
    bills = response.json()
    assert len(bills) == 1
    assert bills[0]["id"] == bill1["id"]


def test_update_bill(client, auth_headers, expense_category):
    created = make_bill(client, auth_headers, category_id=expense_category["id"]).json()

    response = client.put(
        f"/api/bills/{created['id']}",
        json={
            "account_id": None,
            "category_id": expense_category["id"],
            "description": "Updated Bill",
            "amount": 250.0,
            "due_date": "2026-03-20",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Updated Bill"
    assert body["amount"] == 250.0


def test_update_bill_not_found(client, auth_headers):
    response = client.put(
        "/api/bills/999",
        json={
            "account_id": None,
            "category_id": None,
            "description": "Test",
            "amount": 100.0,
            "due_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_bill(client, auth_headers, expense_category):
    created = make_bill(client, auth_headers, category_id=expense_category["id"]).json()

    response = client.delete(f"/api/bills/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/bills", headers=auth_headers)
    assert response.json() == []


def test_delete_bill_not_found(client, auth_headers):
    response = client.delete("/api/bills/999", headers=auth_headers)
    assert response.status_code == 404


def test_pay_bill(client, auth_headers, default_account, expense_category):
    bill = make_bill(
        client, auth_headers, category_id=expense_category["id"], amount=150.0
    ).json()

    response = client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["paid"] is True
    assert body["paid_transaction_id"] is not None
    assert body["account_id"] == default_account["id"]

    # Verify transaction was created (today's month/year, since transaction is created on payment date)
    today = date.today()
    tx_response = client.get(
        f"/api/transactions?month={today.month}&year={today.year}", headers=auth_headers
    )
    transactions = tx_response.json()
    assert len(transactions) == 1
    tx = transactions[0]
    assert tx["amount"] == 150.0
    assert tx["description"] == bill["description"]
    assert tx["type"] == "expense"
    assert tx["category_id"] == expense_category["id"]
    assert tx["account_id"] == default_account["id"]
    assert tx["id"] == body["paid_transaction_id"]


def test_pay_bill_not_found(client, auth_headers, default_account):
    response = client.post(
        "/api/bills/999/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_pay_bill_invalid_account(client, auth_headers, expense_category):
    bill = make_bill(client, auth_headers, category_id=expense_category["id"]).json()

    response = client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": 999},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_pay_bill_already_paid(client, auth_headers, default_account, expense_category):
    bill = make_bill(client, auth_headers, category_id=expense_category["id"]).json()

    # Pay it once
    client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )

    # Try to pay again
    response = client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "already paid" in response.json()["detail"]


def test_pay_bill_creates_correct_transaction_balance(client, auth_headers, default_account, expense_category):
    """Verify that paying a bill creates a proper transaction with correct balance impact."""
    # Get initial balance
    initial_balance_response = client.get("/api/accounts", headers=auth_headers)
    initial_balance = initial_balance_response.json()[0]["balance"]

    # Create and pay a bill
    bill = make_bill(
        client, auth_headers, category_id=expense_category["id"], amount=100.0
    ).json()
    client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )

    # Get new balance
    new_balance_response = client.get("/api/accounts", headers=auth_headers)
    new_balance = new_balance_response.json()[0]["balance"]

    # Balance should have decreased by the bill amount
    assert new_balance == initial_balance - 100.0


def test_pay_bill_does_not_delete_linked_transaction_on_bill_delete(client, auth_headers, default_account, expense_category):
    """Deleting a paid bill should not delete the linked transaction."""
    bill = make_bill(client, auth_headers, category_id=expense_category["id"]).json()

    # Pay the bill
    pay_response = client.post(
        f"/api/bills/{bill['id']}/pay",
        json={"account_id": default_account["id"]},
        headers=auth_headers,
    )
    tx_id = pay_response.json()["paid_transaction_id"]

    # Delete the bill
    client.delete(f"/api/bills/{bill['id']}", headers=auth_headers)

    # Transaction should still exist (in current month/year when paid)
    today = date.today()
    tx_response = client.get(
        f"/api/transactions?month={today.month}&year={today.year}", headers=auth_headers
    )
    transactions = tx_response.json()
    assert len(transactions) == 1
    assert transactions[0]["id"] == tx_id


def test_bills_require_auth(client):
    response = client.get("/api/bills")
    assert response.status_code == 401


# Cross-user isolation test
@pytest.fixture()
def user_a_bill(client, db_session):
    """Set up user A with a bill."""
    crud.create_user(db_session, username="alice", name="Alice", password_hash=auth.hash_password("alicepass123"))
    response = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    category = client.post(
        "/api/categories",
        json={"name": "Alice Utilities", "type": "expense", "color": "#FF0000"},
        headers=headers,
    ).json()

    bill = client.post(
        "/api/bills",
        json={
            "account_id": None,
            "category_id": category["id"],
            "description": "Alice Bill",
            "amount": 100.0,
            "due_date": "2026-03-15",
        },
        headers=headers,
    ).json()

    return {"headers": headers, "bill": bill}


def test_bills_cross_user_isolation(client, auth_headers, user_a_bill, expense_category):
    # Admin user creates their own bill
    admin_bill = make_bill(client, auth_headers, category_id=expense_category["id"]).json()

    # Admin user should only see their own bill
    response = client.get("/api/bills", headers=auth_headers)
    ids = {b["id"] for b in response.json()}
    assert admin_bill["id"] in ids
    assert user_a_bill["bill"]["id"] not in ids

    # Admin cannot update Alice's bill
    response = client.put(
        f"/api/bills/{user_a_bill['bill']['id']}",
        json={
            "account_id": None,
            "category_id": None,
            "description": "Hijacked",
            "amount": 9999.0,
            "due_date": "2026-03-15",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404

    # Admin cannot delete Alice's bill
    response = client.delete(f"/api/bills/{user_a_bill['bill']['id']}", headers=auth_headers)
    assert response.status_code == 404

    # Admin cannot pay Alice's bill
    response = client.post(
        f"/api/bills/{user_a_bill['bill']['id']}/pay",
        json={"account_id": 1},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_bills_with_due_date_older_than_3_years_does_not_500(client, auth_headers, db_session):
    """Regression test: GET /bills must not re-validate the date-range
    guardrail on read -- see the identical bug/fix for InvestmentMovementOut.
    BillOut used to inherit the guardrail from BillBase, so an old paid bill
    (perfectly valid when created) would 500 the whole list once its
    due_date aged past the rolling 3-year window.
    """
    user = crud.get_user_by_username(db_session, "admin")

    old_bill = models.Bill(
        user_id=user.id,
        description="Old paid bill",
        amount=42.0,
        due_date=date.today() - timedelta(days=365 * 4),
        paid=True,
    )
    db_session.add(old_bill)
    db_session.commit()

    response = client.get("/api/bills", headers=auth_headers)
    assert response.status_code == 200
    due_dates = [b["due_date"] for b in response.json()]
    assert old_bill.due_date.isoformat() in due_dates
