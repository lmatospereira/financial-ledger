"""GET/POST/PUT/DELETE /api/goals -- scoped to the current user.

Goals represent financial targets with optional target dates, and progress
is automatically calculated from the linked account's balance.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/api/goals",
    tags=["goals"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.GoalOut])
def list_goals(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goals = crud.get_goals(db, current_user.id)
    result = []
    for goal in goals:
        account = crud.get_account(db, goal.account_id, current_user.id)
        current_amount = crud.get_account_balance(db, goal.account_id)
        progress_percent = min(max(current_amount / goal.target_amount, 0), 1) if goal.target_amount > 0 else 0
        result.append(
            schemas.GoalOut(
                id=goal.id,
                name=goal.name,
                target_amount=goal.target_amount,
                target_date=goal.target_date,
                color=goal.color,
                created_at=goal.created_at,
                account=schemas.AccountRef.model_validate(account) if account else None,
                current_amount=current_amount,
                progress_percent=progress_percent,
            )
        )
    return result


@router.post("", response_model=schemas.GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal: schemas.GoalCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify account belongs to current user
    account = crud.get_account(db, goal.account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    db_goal = crud.create_goal(db, current_user.id, goal)
    current_amount = crud.get_account_balance(db, db_goal.account_id)
    progress_percent = min(max(current_amount / db_goal.target_amount, 0), 1) if db_goal.target_amount > 0 else 0
    return schemas.GoalOut(
        id=db_goal.id,
        name=db_goal.name,
        target_amount=db_goal.target_amount,
        target_date=db_goal.target_date,
        color=db_goal.color,
        created_at=db_goal.created_at,
        account=schemas.AccountRef.model_validate(account),
        current_amount=current_amount,
        progress_percent=progress_percent,
    )


@router.put("/{goal_id}", response_model=schemas.GoalOut)
def update_goal(
    goal_id: int,
    goal: schemas.GoalUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_goal = crud.get_goal(db, goal_id, current_user.id)
    if db_goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    # Verify account belongs to current user (if changed)
    if goal.account_id is not None and goal.account_id != db_goal.account_id:
        account = crud.get_account(db, goal.account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    db_goal = crud.update_goal(db, db_goal, goal)
    current_amount = crud.get_account_balance(db, db_goal.account_id)
    progress_percent = min(max(current_amount / db_goal.target_amount, 0), 1) if db_goal.target_amount > 0 else 0
    return schemas.GoalOut(
        id=db_goal.id,
        name=db_goal.name,
        target_amount=db_goal.target_amount,
        target_date=db_goal.target_date,
        color=db_goal.color,
        created_at=db_goal.created_at,
        account=schemas.AccountRef.model_validate(crud.get_account(db, db_goal.account_id, current_user.id)),
        current_amount=current_amount,
        progress_percent=progress_percent,
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_goal = crud.get_goal(db, goal_id, current_user.id)
    if db_goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    crud.delete_goal(db, db_goal)
    return None
