"""GET /api/reports/monthly-trend, GET /api/reports/by-category -- scoped to
the current user, consolidated across all of their accounts.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(get_current_user)])


@router.get("/monthly-trend", response_model=list[schemas.MonthlyTrendOut])
def monthly_trend(
    year: int = Query(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_monthly_trend(db, current_user.id, year)


@router.get("/by-category", response_model=list[schemas.CategoryTotalOut])
def by_category(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_category_totals(db, current_user.id, month, year)
