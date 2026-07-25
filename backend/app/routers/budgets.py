"""GET/POST/PUT/DELETE /api/budgets -- scoped to the current user.

Each budget is a monthly spending limit per category. Only one budget per
(user_id, category_id) pair. GET /api/budgets/status?month=&year= returns
budget status with actual spending for the given month.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/api/budgets",
    tags=["budgets"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.BudgetOut])
def list_budgets(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return crud.get_budgets(db, current_user.id)


@router.post("", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: schemas.BudgetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify category belongs to current user
    category = crud.get_category(db, budget.category_id, current_user.id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Check if budget already exists for this category
    existing = crud.get_budget_by_category(db, current_user.id, budget.category_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget already exists for this category; use PUT to update",
        )

    db_budget = crud.create_budget(db, current_user.id, budget)
    return db_budget


@router.put("/{budget_id}", response_model=schemas.BudgetOut)
def update_budget(
    budget_id: int,
    budget: schemas.BudgetUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_budget = crud.get_budget(db, budget_id, current_user.id)
    if db_budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    # Verify new category belongs to current user (if changed)
    if budget.category_id != db_budget.category_id:
        category = crud.get_category(db, budget.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        # Check if budget already exists for the new category
        existing = crud.get_budget_by_category(db, current_user.id, budget.category_id)
        if existing is not None and existing.id != budget_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Budget already exists for this category",
            )

    db_budget = crud.update_budget(db, db_budget, budget)
    return db_budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_budget = crud.get_budget(db, budget_id, current_user.id)
    if db_budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    crud.delete_budget(db, db_budget)
    return None


@router.get("/status", response_model=list[schemas.BudgetStatusOut])
def budget_status(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")
    if year < 1:
        raise HTTPException(status_code=422, detail="year must be a positive integer")
    return crud.get_budget_status(db, current_user.id, month, year)
