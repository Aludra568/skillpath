from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import check_review, check_view, current_user
from ..models import Issue, Plan, PlanItem, Skill, User
from ..schemas import PlanItemIn, PlanItemOut, PlanOut
from ..services import is_overdue, make_progress

router = APIRouter(prefix="/api/users/{user_id}/plan", tags=["plans"])


def plan_out(db: Session, plan: Plan) -> PlanOut:
    today = date.today()
    items = []
    for item in plan.items:
        data = PlanItemOut.model_validate(item)
        data.is_overdue = is_overdue(item, today)
        items.append(data)
    issues = len(
        db.scalars(
            select(Issue).where(
                Issue.employee_id == plan.user_id, Issue.is_resolved.is_(False)
            )
        ).all()
    )
    return PlanOut(
        id=plan.id,
        year=plan.year,
        items=items,
        progress=make_progress(list(plan.items), issues, today),
    )


def find_plan(db: Session, user_id: int, year: int) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.user_id == user_id, Plan.year == year))


@router.get("", response_model=PlanOut | None)
def get_plan(
    user_id: int,
    year: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    check_view(db, actor, user_id)
    plan = find_plan(db, user_id, year or date.today().year)
    return plan_out(db, plan) if plan else None


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    user_id: int,
    year: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    check_review(db, actor, user_id)
    year = year or date.today().year
    if find_plan(db, user_id, year):
        raise HTTPException(409, "План на этот год уже есть")
    plan = Plan(user_id=user_id, year=year)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan_out(db, plan)


@router.post("/items", response_model=PlanOut, status_code=201)
def add_item(
    user_id: int,
    data: PlanItemIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    check_review(db, actor, user_id)
    plan = find_plan(db, user_id, date.today().year)
    if plan is None:
        raise HTTPException(404, "Сначала создайте план")
    if db.get(Skill, data.skill_id) is None:
        raise HTTPException(400, "Скилл не найден")
    if any(item.skill_id == data.skill_id for item in plan.items):
        raise HTTPException(409, "Этот скилл уже есть в плане")

    db.add(PlanItem(plan_id=plan.id, skill_id=data.skill_id, target_date=data.target_date))
    db.commit()
    db.refresh(plan)
    return plan_out(db, plan)


@router.delete("/items/{item_id}", response_model=PlanOut)
def delete_item(
    user_id: int, item_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    check_review(db, actor, user_id)
    item = db.get(PlanItem, item_id)
    if item is None or item.plan.user_id != user_id:
        raise HTTPException(404, "Пункт плана не найден")
    plan = item.plan
    db.delete(item)
    db.commit()
    db.refresh(plan)
    return plan_out(db, plan)
