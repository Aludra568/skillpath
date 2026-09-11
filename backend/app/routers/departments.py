from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import managed_department_ids, subtree_ids
from ..db import get_db
from ..deps import admin_only, current_user
from ..models import Department, User
from ..schemas import DepartmentIn, DepartmentNode, DepartmentOut, UserBrief

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("/tree", response_model=list[DepartmentNode])
def tree(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    """Дерево подразделений в зоне ответственности пользователя."""
    allowed = managed_department_ids(db, actor)
    departments = db.scalars(select(Department).order_by(Department.name)).all()
    if allowed is not None:
        departments = [d for d in departments if d.id in allowed]

    users = db.scalars(select(User).order_by(User.full_name)).all()
    heads = {u.id: u.full_name for u in users}

    nodes: dict[int, DepartmentNode] = {}
    for department in departments:
        nodes[department.id] = DepartmentNode(
            id=department.id,
            name=department.name,
            parent_id=department.parent_id,
            head_id=department.head_id,
            head_name=heads.get(department.head_id) if department.head_id else None,
            members=[
                UserBrief.model_validate(u) for u in users if u.department_id == department.id
            ],
            children=[],
        )

    roots: list[DepartmentNode] = []
    for node in nodes.values():
        parent = nodes.get(node.parent_id) if node.parent_id else None
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)
    return roots


@router.get("", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    allowed = managed_department_ids(db, actor)
    departments = db.scalars(select(Department).order_by(Department.name)).all()
    if allowed is not None:
        departments = [d for d in departments if d.id in allowed]
    return departments


@router.post("", response_model=DepartmentOut, status_code=201)
def add_department(
    data: DepartmentIn, db: Session = Depends(get_db), _: User = Depends(admin_only)
):
    if data.parent_id and db.get(Department, data.parent_id) is None:
        raise HTTPException(400, "Родительское подразделение не найдено")
    department = Department(name=data.name.strip(), parent_id=data.parent_id, head_id=data.head_id)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.patch("/{department_id}", response_model=DepartmentOut)
def edit_department(
    department_id: int,
    data: DepartmentIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(404, "Подразделение не найдено")
    # Перенос внутрь собственного поддерева зациклил бы дерево.
    if data.parent_id and data.parent_id in subtree_ids(db, department_id):
        raise HTTPException(400, "Нельзя перенести подразделение внутрь самого себя")
    department.name = data.name.strip()
    department.parent_id = data.parent_id
    department.head_id = data.head_id
    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=204, response_model=None)
def delete_department(
    department_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> None:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(404, "Подразделение не найдено")
    if db.scalar(select(Department).where(Department.parent_id == department_id)):
        raise HTTPException(409, "Сначала перенесите вложенные подразделения")
    if db.scalar(select(User).where(User.department_id == department_id)):
        raise HTTPException(409, "В подразделении есть сотрудники")
    db.delete(department)
    db.commit()
