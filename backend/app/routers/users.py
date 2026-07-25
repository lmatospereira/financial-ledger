"""GET/POST/PUT/DELETE /api/users (admin only), PUT /api/users/me/password
(any authenticated user).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, crud, models, schemas
from app.auth import get_current_admin_user, get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[schemas.UserOut])
def list_users(
    current_user: models.User = Depends(get_current_admin_user), db: Session = Depends(get_db)
):
    return crud.get_users(db)


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    if crud.get_user_by_username(db, user.username) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    return crud.create_user(
        db,
        username=user.username,
        name=user.name,
        password_hash=auth.hash_password(user.password),
        is_admin=user.is_admin,
    )


@router.put("/me/password", response_model=schemas.UserOut)
def change_password(
    payload: schemas.PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
        )
    return crud.update_user_password(db, current_user, auth.hash_password(payload.new_password))


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    db_user = crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    existing = crud.get_user_by_username(db, user.username)
    if existing is not None and existing.id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    return crud.update_user(db, db_user, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    db_user = crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    crud.delete_user(db, db_user)
    return None
