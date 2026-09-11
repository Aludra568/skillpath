"""Справочник направлений и скиллов. Менять может только администратор."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import admin_only, current_user
from ..models import Direction, PlanItem, Skill, User
from ..schemas import DirectionIn, DirectionOut, SkillIn, SkillOut

router = APIRouter(prefix="/api", tags=["catalog"])


def own_direction(db: Session, admin: User, direction_id: int) -> Direction:
    direction = db.get(Direction, direction_id)
    if direction is None or direction.company_id != admin.company_id:
        raise HTTPException(404, "Направление не найдено")
    return direction


def own_skill(db: Session, admin: User, skill_id: int) -> Skill:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(404, "Скилл не найден")
    own_direction(db, admin, skill.direction_id)
    return skill


@router.get("/directions", response_model=list[DirectionOut])
def directions(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return db.scalars(
        select(Direction).where(Direction.company_id == actor.company_id).order_by(Direction.code)
    ).all()


@router.post("/directions", response_model=DirectionOut, status_code=201)
def add_direction(data: DirectionIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.scalar(
        select(Direction).where(
            Direction.company_id == admin.company_id, Direction.code == data.code.upper()
        )
    ):
        raise HTTPException(409, "Направление с таким кодом уже есть")
    direction = Direction(
        code=data.code.strip().upper(), name=data.name.strip(), company_id=admin.company_id
    )
    db.add(direction)
    db.commit()
    db.refresh(direction)
    return direction


@router.patch("/directions/{direction_id}", response_model=DirectionOut)
def edit_direction(
    direction_id: int,
    data: DirectionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    direction = own_direction(db, admin, direction_id)
    direction.code = data.code.strip().upper()
    direction.name = data.name.strip()
    db.commit()
    db.refresh(direction)
    return direction


@router.delete("/directions/{direction_id}", status_code=204, response_model=None)
def delete_direction(
    direction_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)
) -> None:
    direction = own_direction(db, admin, direction_id)
    if db.scalar(select(Skill).where(Skill.direction_id == direction_id)):
        raise HTTPException(409, "Сначала удалите скиллы этого направления")
    db.delete(direction)
    db.commit()


@router.get("/skills", response_model=list[SkillOut])
def skills(
    direction_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    # Скиллы принадлежат направлениям, направления — компании.
    query = (
        select(Skill)
        .join(Direction, Direction.id == Skill.direction_id)
        .where(Direction.company_id == actor.company_id)
        .order_by(Skill.name)
    )
    if direction_id is not None:
        query = query.where(Skill.direction_id == direction_id)
    return db.scalars(query).all()


@router.post("/skills", response_model=SkillOut, status_code=201)
def add_skill(data: SkillIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    own_direction(db, admin, data.direction_id)
    skill = Skill(
        name=data.name.strip(), description=data.description, direction_id=data.direction_id
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.patch("/skills/{skill_id}", response_model=SkillOut)
def edit_skill(
    skill_id: int, data: SkillIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    skill = own_skill(db, admin, skill_id)
    own_direction(db, admin, data.direction_id)
    skill.name = data.name.strip()
    skill.description = data.description
    skill.direction_id = data.direction_id
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}", status_code=204, response_model=None)
def delete_skill(skill_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)) -> None:
    skill = own_skill(db, admin, skill_id)
    if db.scalar(select(PlanItem).where(PlanItem.skill_id == skill_id)):
        raise HTTPException(409, "Скилл уже стоит в планах обучения, удалить нельзя")
    db.delete(skill)
    db.commit()
