from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..access import department_path, manager_of, relation, subtree_ids, visible_user_ids
from ..db import get_db
from ..deps import admin_only, check_view, current_user
from ..models import Department, User
from ..schemas import UserIn, UserOut
from ..security import hash_password
from ..services import progress_for_users

router = APIRouter(prefix="/api/users", tags=["users"])


def to_out(db: Session, actor: User, user: User, progress) -> UserOut:
    data = UserOut.model_validate(user)
    data.department_path = department_path(db, user.department_id)
    manager = manager_of(db, user)
    data.manager_name = manager.full_name if manager else None
    data.relation = relation(db, actor, user.id)
    if progress is not None:
        data.progress = progress
    return data


@router.get("", response_model=list[UserOut])
def list_users(
    direction_id: int | None = None,
    department_id: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    """Список сотрудников с фильтрами по направлению и подразделению."""
    query = select(User)

    allowed = visible_user_ids(db, actor)
    if allowed is not None:
        query = query.where(User.id.in_(allowed or {-1}))
    if direction_id is not None:
        query = query.where(User.direction_id == direction_id)
    if department_id is not None:
        # Вложенные подразделения тоже попадают в выборку.
        query = query.where(User.department_id.in_(subtree_ids(db, department_id)))
    if q:
        pattern = f"%{q.strip().lower()}%"
        query = query.where(
            or_(func.lower(User.full_name).like(pattern), func.lower(User.email).like(pattern))
        )

    users = list(db.scalars(query.order_by(User.full_name)).all())
    progress = progress_for_users(db, [u.id for u in users])
    return [to_out(db, actor, user, progress.get(user.id)) for user in users]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    check_view(db, actor, user_id)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Сотрудник не найден")
    return to_out(db, actor, user, progress_for_users(db, [user_id]).get(user_id))


@router.post("", response_model=UserOut, status_code=201)
def add_user(data: UserIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if not data.password:
        raise HTTPException(400, "Нужен пароль")
    if db.scalar(select(User).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(409, "Пользователь с такой почтой уже есть")
    if data.department_id and db.get(Department, data.department_id) is None:
        raise HTTPException(400, "Подразделение не найдено")

    user = User(
        email=data.email.lower(),
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        position=data.position,
        is_admin=data.is_admin,
        direction_id=data.direction_id,
        department_id=data.department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return to_out(db, admin, user, None)


@router.patch("/{user_id}", response_model=UserOut)
def edit_user(
    user_id: int, data: UserIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Сотрудник не найден")
    user.email = data.email.lower()
    user.full_name = data.full_name.strip()
    user.position = data.position
    user.is_admin = data.is_admin
    user.direction_id = data.direction_id
    user.department_id = data.department_id
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return to_out(db, admin, user, None)


@router.delete("/{user_id}", status_code=204, response_model=None)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Сотрудник не найден")
    if user.id == admin.id:
        raise HTTPException(400, "Нельзя удалить самого себя")
    if db.scalar(select(Department).where(Department.head_id == user_id)):
        raise HTTPException(409, "Сотрудник руководит подразделением, сначала назначьте другого")
    db.delete(user)
    db.commit()
