from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .access import can_review, can_view, relation
from .db import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(401, "Требуется авторизация")
    user_id = decode_token(credentials.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "Сессия истекла, войдите заново")
    return user


def admin_only(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Только для администратора")
    return user


def check_view(db: Session, actor: User, employee_id: int) -> str:
    value = relation(db, actor, employee_id)
    if not can_view(value):
        raise HTTPException(403, "Нет доступа к данным этого сотрудника")
    return value


def check_review(db: Session, actor: User, employee_id: int) -> str:
    value = relation(db, actor, employee_id)
    if not can_review(value):
        raise HTTPException(403, "Вести PR этого сотрудника может только его руководитель")
    return value
