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


@router.get("/directions", response_model=list[DirectionOut])
def directions(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Direction).order_by(Direction.code)).all()


@router.post("/directions", response_model=DirectionOut, status_code=201)
def add_direction(data: DirectionIn, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if db.scalar(select(Direction).where(Direction.code == data.code.upper())):
        raise HTTPException(409, "Направление с таким кодом уже есть")
    direction = Direction(code=data.code.strip().upper(), name=data.name.strip())
    db.add(direction)
    db.commit()
    db.refresh(direction)
    return direction


@router.patch("/directions/{direction_id}", response_model=DirectionOut)
def edit_direction(
    direction_id: int,
    data: DirectionIn,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    direction = db.get(Direction, direction_id)
    if direction is None:
        raise HTTPException(404, "Направление не найдено")
    direction.code = data.code.strip().upper()
    direction.name = data.name.strip()
    db.commit()
    db.refresh(direction)
    return direction


@router.delete("/directions/{direction_id}", status_code=204, response_model=None)
def delete_direction(
    direction_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> None:
    direction = db.get(Direction, direction_id)
    if direction is None:
        raise HTTPException(404, "Направление не найдено")
    if db.scalar(select(Skill).where(Skill.direction_id == direction_id)):
        raise HTTPException(409, "Сначала удалите скиллы этого направления")
    db.delete(direction)
    db.commit()


@router.get("/skills", response_model=list[SkillOut])
def skills(
    direction_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    query = select(Skill).order_by(Skill.name)
    if direction_id is not None:
        query = query.where(Skill.direction_id == direction_id)
    return db.scalars(query).all()


@router.post("/skills", response_model=SkillOut, status_code=201)
def add_skill(data: SkillIn, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if db.get(Direction, data.direction_id) is None:
        raise HTTPException(400, "Направление не найдено")
    skill = Skill(
        name=data.name.strip(), description=data.description, direction_id=data.direction_id
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.patch("/skills/{skill_id}", response_model=SkillOut)
def edit_skill(
    skill_id: int, data: SkillIn, db: Session = Depends(get_db), _: User = Depends(admin_only)
):
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(404, "Скилл не найден")
    skill.name = data.name.strip()
    skill.description = data.description
    skill.direction_id = data.direction_id
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}", status_code=204, response_model=None)
def delete_skill(skill_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)) -> None:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(404, "Скилл не найден")
    if db.scalar(select(PlanItem).where(PlanItem.skill_id == skill_id)):
        raise HTTPException(409, "Скилл уже стоит в планах обучения, удалить нельзя")
    db.delete(skill)
    db.commit()
