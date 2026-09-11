from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import managed_department_ids, subtree_ids, visible_user_ids
from ..db import get_db
from ..deps import check_view, current_user
from ..models import Department, Issue, Meeting, Plan, PlanItem, User
from ..schemas import DepartmentStats, EmployeeStats, Event, PlanItemOut
from ..services import is_overdue, progress_for_users, total_progress
from .meetings import issue_out
from .users import to_out

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("/departments", response_model=list[DepartmentStats])
def departments_stats(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    """Сводка по каждому подразделению в зоне ответственности."""
    allowed = managed_department_ids(db, actor)
    departments = db.scalars(select(Department).order_by(Department.name)).all()
    if allowed is not None:
        departments = [d for d in departments if d.id in allowed]

    result = []
    for department in departments:
        ids = subtree_ids(db, department.id)
        users = list(db.scalars(select(User).where(User.department_id.in_(ids))).all())
        progress = progress_for_users(db, [u.id for u in users])
        held = db.scalars(
            select(Meeting).where(
                Meeting.employee_id.in_([u.id for u in users] or [-1]),
                Meeting.held_at.is_not(None),
            )
        ).all()

        at_risk = [u for u in users if progress[u.id].overdue > 0 or progress[u.id].issues > 0]
        result.append(
            DepartmentStats(
                id=department.id,
                name=department.name,
                employees=len(users),
                progress=total_progress(list(progress.values())),
                meetings_held=len(held),
                at_risk=[to_out(db, actor, u, progress[u.id]) for u in at_risk[:5]],
            )
        )
    return result


@router.get("/employees/{user_id}", response_model=EmployeeStats)
def employee_stats(user_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    check_view(db, actor, user_id)
    if db.get(User, user_id) is None:
        raise HTTPException(404, "Сотрудник не найден")

    today = date.today()
    plan = db.scalar(select(Plan).where(Plan.user_id == user_id, Plan.year == today.year))
    items: list[PlanItem] = list(plan.items) if plan else []

    def to_item(item: PlanItem) -> PlanItemOut:
        data = PlanItemOut.model_validate(item)
        data.is_overdue = is_overdue(item, today)
        return data

    issues = db.scalars(
        select(Issue).where(Issue.employee_id == user_id, Issue.is_resolved.is_(False))
    ).all()

    meetings = list(
        db.scalars(
            select(Meeting).where(Meeting.employee_id == user_id).order_by(Meeting.scheduled_at)
        ).all()
    )
    now = datetime.now(timezone.utc)
    upcoming = [m for m in meetings if m.held_at is None and aware(m.scheduled_at) >= now]

    return EmployeeStats(
        progress=progress_for_users(db, [user_id])[user_id],
        confirmed=[to_item(i) for i in items if i.is_confirmed],
        overdue=[to_item(i) for i in items if is_overdue(i, today)],
        issues=[issue_out(issue) for issue in issues],
        meetings_held=len([m for m in meetings if m.held_at is not None]),
        next_meeting_at=aware(upcoming[0].scheduled_at) if upcoming else None,
    )


# --- Ближайшие события ----------------------------------------------------

events_router = APIRouter(prefix="/api/events", tags=["events"])


@events_router.get("", response_model=list[Event])
def events(
    days: int = 30,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    """Встречи и плановые даты подтверждения скиллов.

    По умолчанию — ближайшие дни, для календаря передаём период месяца.
    """
    today = date_from or date.today()
    until = date_to or (date.today() + timedelta(days=days))
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = datetime.combine(until, time.max, tzinfo=timezone.utc)

    allowed = visible_user_ids(db, actor)

    meetings_query = select(Meeting).where(
        Meeting.scheduled_at >= start, Meeting.scheduled_at <= end
    )
    if allowed is not None:
        meetings_query = meetings_query.where(Meeting.employee_id.in_(allowed or {-1}))

    result: list[Event] = []
    for meeting in db.scalars(meetings_query).all():
        result.append(
            Event(
                kind="meeting",
                id=meeting.id,
                date=aware(meeting.scheduled_at),
                title=meeting.title or "PR-встреча",
                employee_id=meeting.employee_id,
                employee_name=meeting.employee.full_name,
                done=meeting.held_at is not None,
            )
        )

    items_query = (
        select(PlanItem, Plan.user_id)
        .join(Plan, Plan.id == PlanItem.plan_id)
        .where(PlanItem.target_date >= today, PlanItem.target_date <= until)
    )
    if allowed is not None:
        items_query = items_query.where(Plan.user_id.in_(allowed or {-1}))

    users = {u.id: u.full_name for u in db.scalars(select(User)).all()}
    for item, owner_id in db.execute(items_query).all():
        result.append(
            Event(
                kind="deadline",
                id=item.id,
                date=datetime.combine(item.target_date, time(9), tzinfo=timezone.utc),
                title=item.skill.name,
                employee_id=owner_id,
                employee_name=users.get(owner_id, ""),
                done=item.is_confirmed,
            )
        )

    result.sort(key=lambda event: event.date)
    return result
