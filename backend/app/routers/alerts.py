"""GET /api/alerts/upcoming -- unified view of upcoming financial obligations.

Combines bills, recurring transactions, and installment transactions
to show all upcoming due dates and overdue items.
"""
from datetime import date, timedelta
from calendar import monthrange

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/api/alerts",
    tags=["alerts"],
    dependencies=[Depends(get_current_user)],
)


def _compute_next_recurring_date(
    rt: models.RecurringTransaction, today: date
) -> date | None:
    """Compute the next occurrence date for a recurring transaction.

    If today's day <= day_of_month, next occurrence is this month on day_of_month.
    Otherwise, next occurrence is next month on day_of_month.
    Clamps to the month's last day if day_of_month exceeds it (e.g., day 31 in Feb).
    Returns None if the computed date falls outside the rule's active period.
    """
    # If we've already passed this month's occurrence, move to next month
    if today.day >= rt.day_of_month:
        # Next month
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1)
        else:
            next_month = today.replace(month=today.month + 1)
    else:
        # This month
        next_month = today.replace(day=1)

    # Clamp day to the last day of the month if needed
    _, days_in_month = monthrange(next_month.year, next_month.month)
    day = min(rt.day_of_month, days_in_month)
    next_occurrence = next_month.replace(day=day)

    # Check if this date is within the rule's active period
    if next_occurrence < rt.start_date:
        return None
    if rt.end_date is not None and next_occurrence > rt.end_date:
        return None

    return next_occurrence


@router.get("/upcoming", response_model=list[schemas.UpcomingAlertOut])
def get_upcoming_alerts(
    days: int = Query(7, ge=1, le=90),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all upcoming/overdue financial obligations within the specified days window.

    Args:
        days: Number of days to look ahead (default 7, max 90)

    Returns:
        Unified list of alerts sorted by due_date ascending, combining:
        - Unpaid bills with due_date <= today + days
        - Next occurrences of active recurring transactions
        - Materialized installment transactions
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    alerts = []

    # 1. Bills: unpaid with due_date <= today + days
    bills = crud.get_bills(db, current_user.id, paid=False)
    for bill in bills:
        if bill.due_date <= end_date:
            account = crud.get_account(db, bill.account_id, current_user.id) if bill.account_id else None
            category = crud.get_category(db, bill.category_id, current_user.id) if bill.category_id else None
            alerts.append(
                schemas.UpcomingAlertOut(
                    kind="bill",
                    id=bill.id,
                    description=bill.description,
                    amount=bill.amount,
                    due_date=bill.due_date,
                    is_overdue=bill.due_date < today,
                    account=schemas.AccountRef.model_validate(account) if account else None,
                    category=schemas.CategoryOut.model_validate(category) if category else None,
                )
            )

    # 2. Recurring transactions: next occurrence within [today, today + days]
    recurring_txs = crud.get_recurring_transactions(db, current_user.id)
    for rt in recurring_txs:
        if not rt.active:
            continue
        next_occurrence = _compute_next_recurring_date(rt, today)
        if next_occurrence is not None and today <= next_occurrence <= end_date:
            account = crud.get_account(db, rt.account_id, current_user.id)
            category = crud.get_category(db, rt.category_id, current_user.id) if rt.category_id else None
            alerts.append(
                schemas.UpcomingAlertOut(
                    kind="recurring",
                    id=rt.id,
                    description=rt.description,
                    amount=rt.amount,
                    due_date=next_occurrence,
                    is_overdue=False,  # Recurring transactions can't be overdue in this context
                    account=schemas.AccountRef.model_validate(account) if account else None,
                    category=schemas.CategoryOut.model_validate(category) if category else None,
                )
            )

    # 3. Installment transactions: materialized with date in [today, today + days]
    installment_txs = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.type == "expense",
            models.Transaction.installment_number.isnot(None),
            models.Transaction.date >= today,
            models.Transaction.date <= end_date,
        )
        .all()
    )
    for tx in installment_txs:
        account = crud.get_account(db, tx.account_id, current_user.id)
        category = crud.get_category(db, tx.category_id, current_user.id) if tx.category_id else None
        alerts.append(
            schemas.UpcomingAlertOut(
                kind="installment",
                id=tx.id,
                description=tx.description,
                amount=tx.amount,
                due_date=tx.date,
                is_overdue=tx.date < today,
                account=schemas.AccountRef.model_validate(account) if account else None,
                category=schemas.CategoryOut.model_validate(category) if category else None,
            )
        )

    # Sort by due_date ascending
    alerts.sort(key=lambda a: a.due_date)
    return alerts
