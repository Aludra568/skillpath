"""Права считаются относительно конкретного сотрудника, а не по глобальной роли.

Два уровня ограничений:

1. Компания. Пользователь не видит и не может тронуть ничего за пределами своей
   компании — даже администратор. Компании полностью изолированы.
2. Дерево подразделений внутри компании. Руководитель узла ведёт всех, кто есть
   в этом узле и во всех вложенных, на любую глубину.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Department, User


def company_departments(db: Session, company_id: int) -> list[Department]:
    return list(
        db.scalars(
            select(Department).where(Department.company_id == company_id).order_by(Department.name)
        ).all()
    )


def _children(db: Session, company_id: int) -> dict[int | None, list[int]]:
    children: dict[int | None, list[int]] = {}
    for dept in company_departments(db, company_id):
        children.setdefault(dept.parent_id, []).append(dept.id)
    return children


def subtree_ids(db: Session, company_id: int, root_id: int) -> set[int]:
    """Подразделение и все вложенные в него."""
    children = _children(db, company_id)
    found: set[int] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(children.get(current, []))
    return found


def department_path(db: Session, company_id: int, department_id: int | None) -> list[str]:
    """Путь от корня до подразделения, для показа в интерфейсе."""
    if department_id is None:
        return []
    by_id = {d.id: d for d in company_departments(db, company_id)}
    path: list[str] = []
    current = by_id.get(department_id)
    while current is not None:
        path.append(current.name)
        current = by_id.get(current.parent_id) if current.parent_id else None
    path.reverse()
    return path


def managed_department_ids(db: Session, actor: User) -> set[int]:
    """Подразделения в зоне ответственности. У администратора — все в его компании."""
    departments = company_departments(db, actor.company_id)
    if actor.is_admin:
        return {d.id for d in departments}
    result: set[int] = set()
    for dept in departments:
        if dept.head_id == actor.id:
            result |= subtree_ids(db, actor.company_id, dept.id)
    return result


def company_user_ids(db: Session, company_id: int) -> set[int]:
    return set(db.scalars(select(User.id).where(User.company_id == company_id)).all())


def subordinate_ids(db: Session, actor: User) -> set[int]:
    """Все подчинённые внутри компании, без самого actor."""
    if actor.is_admin:
        return company_user_ids(db, actor.company_id) - {actor.id}

    departments = managed_department_ids(db, actor)
    if not departments:
        return set()
    found = set(
        db.scalars(
            select(User.id).where(
                User.company_id == actor.company_id, User.department_id.in_(departments)
            )
        ).all()
    )
    return found - {actor.id}


def visible_user_ids(db: Session, actor: User) -> set[int]:
    """Кого actor вправе видеть: себя и подчинённых, всегда внутри своей компании."""
    return subordinate_ids(db, actor) | {actor.id}


def relation(db: Session, actor: User, employee_id: int) -> str:
    """admin | manager | self | none"""
    if actor.id == employee_id:
        return "self"
    target = db.get(User, employee_id)
    # Чужая компания недоступна никому, включая администратора.
    if target is None or target.company_id != actor.company_id:
        return "none"
    if actor.is_admin:
        return "admin"
    if employee_id in subordinate_ids(db, actor):
        return "manager"
    return "none"


def can_view(value: str) -> bool:
    return value != "none"


def can_review(value: str) -> bool:
    """Может вести PR: планировать скиллы, проводить встречи, заводить проблемы."""
    return value in ("admin", "manager")


def manager_of(db: Session, user: User) -> User | None:
    """Руководитель сотрудника — глава его подразделения.

    Если сотрудник сам возглавляет своё подразделение, берём главу родительского.
    """
    if user.department_id is None:
        return None
    departments = {d.id: d for d in company_departments(db, user.company_id)}
    current = departments.get(user.department_id)
    while current is not None:
        if current.head_id and current.head_id != user.id:
            return db.get(User, current.head_id)
        current = departments.get(current.parent_id) if current.parent_id else None
    return None
