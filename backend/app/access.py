"""Права считаются относительно конкретного сотрудника, а не по глобальной роли.

Всё строится на дереве подразделений: руководитель узла ведёт всех, кто есть
в этом узле и во всех вложенных, на любую глубину.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Department, User


def _children(db: Session) -> dict[int | None, list[int]]:
    children: dict[int | None, list[int]] = {}
    for dept_id, parent_id in db.execute(select(Department.id, Department.parent_id)).all():
        children.setdefault(parent_id, []).append(dept_id)
    return children


def subtree_ids(db: Session, root_id: int) -> set[int]:
    """Подразделение и все вложенные в него."""
    children = _children(db)
    found: set[int] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(children.get(current, []))
    return found


def department_path(db: Session, department_id: int | None) -> list[str]:
    """Путь от корня до подразделения, для показа в интерфейсе."""
    if department_id is None:
        return []
    by_id = {d.id: d for d in db.scalars(select(Department)).all()}
    path: list[str] = []
    current = by_id.get(department_id)
    while current is not None:
        path.append(current.name)
        current = by_id.get(current.parent_id) if current.parent_id else None
    path.reverse()
    return path


def managed_department_ids(db: Session, actor: User) -> set[int] | None:
    """Подразделения в зоне ответственности. None у админа — значит все."""
    if actor.is_admin:
        return None
    result: set[int] = set()
    for dept_id, head_id in db.execute(select(Department.id, Department.head_id)).all():
        if head_id == actor.id:
            result |= subtree_ids(db, dept_id)
    return result


def subordinate_ids(db: Session, actor: User) -> set[int]:
    """Все подчинённые, без самого actor."""
    departments = managed_department_ids(db, actor)
    query = select(User.id)
    if departments is not None:
        if not departments:
            return set()
        query = query.where(User.department_id.in_(departments))
    return {user_id for user_id in db.scalars(query).all() if user_id != actor.id}


def visible_user_ids(db: Session, actor: User) -> set[int] | None:
    """Кого actor вправе видеть. None — всех."""
    if actor.is_admin:
        return None
    return subordinate_ids(db, actor) | {actor.id}


def relation(db: Session, actor: User, employee_id: int) -> str:
    """admin | manager | self | none"""
    if actor.is_admin:
        return "admin"
    if actor.id == employee_id:
        return "self"
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
    departments = {d.id: d for d in db.scalars(select(Department)).all()}
    current = departments.get(user.department_id)
    while current is not None:
        if current.head_id and current.head_id != user.id:
            return db.get(User, current.head_id)
        current = departments.get(current.parent_id) if current.parent_id else None
    return None
