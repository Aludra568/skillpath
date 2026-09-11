from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import department_path, manager_of, subordinate_ids
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import ChangePassword, LoginRequest, Me, RegisterRequest, TokenResponse, UserOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Самостоятельная регистрация.

    Первый зарегистрировавшийся становится администратором — это владелец
    компании, который дальше заводит структуру и распределяет остальных.
    Все следующие приходят без подразделения, пока администратор их не добавит.
    """
    email = data.email.strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(409, "Пользователь с такой почтой уже зарегистрирован")

    is_first = db.scalar(select(User.id)) is None
    user = User(
        email=email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        position=data.position.strip(),
        is_admin=is_first,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.strip().lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return TokenResponse(access_token=create_token(user.id))


@router.get("/me", response_model=Me)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Me:
    manager = manager_of(db, user)
    data = UserOut.model_validate(user)
    data.department_path = department_path(db, user.department_id)
    data.manager_name = manager.full_name if manager else None
    data.relation = "self"
    return Me(user=data, is_admin=user.is_admin, subordinates=len(subordinate_ids(db, user)))


@router.post("/change-password", status_code=204, response_model=None)
def change_password(
    data: ChangePassword,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Текущий пароль указан неверно")
    user.password_hash = hash_password(data.new_password)
    db.commit()


@router.get("/needs-setup", response_model=dict)
def needs_setup(db: Session = Depends(get_db)) -> dict:
    """Пуста ли система. Нужно экрану входа, чтобы позвать первого владельца."""
    return {"empty": db.scalar(select(User.id)) is None}
