"""Расчёт прогресса. Используется в списках, планах и аналитике."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Issue, Plan, PlanItem
from .schemas import Progress


def is_overdue(item: PlanItem, today: date) -> bool:
    return not item.is_confirmed and item.target_date < today


def make_progress(items: list[PlanItem], issues: int, today: date) -> Progress:
    confirmed = sum(1 for item in items if item.is_confirmed)
    return Progress(
        total=len(items),
        confirmed=confirmed,
        overdue=sum(1 for item in items if is_overdue(item, today)),
        issues=issues,
        percent=round(confirmed / len(items) * 100) if items else 0,
    )


def progress_for_users(db: Session, user_ids: list[int], year: int | None = None) -> dict[int, Progress]:
    """Считает прогресс сразу для списка сотрудников."""
    if not user_ids:
        return {}
    today = date.today()

    query = (
        select(Plan.user_id, PlanItem)
        .join(PlanItem, PlanItem.plan_id == Plan.id)
        .where(Plan.user_id.in_(user_ids))
    )
    if year is not None:
        query = query.where(Plan.year == year)

    items: dict[int, list[PlanItem]] = {user_id: [] for user_id in user_ids}
    for user_id, item in db.execute(query).all():
        items[user_id].append(item)

    issues: dict[int, int] = {user_id: 0 for user_id in user_ids}
    open_issues = db.scalars(
        select(Issue).where(Issue.employee_id.in_(user_ids), Issue.is_resolved.is_(False))
    ).all()
    for issue in open_issues:
        issues[issue.employee_id] = issues.get(issue.employee_id, 0) + 1

    return {
        user_id: make_progress(items[user_id], issues.get(user_id, 0), today) for user_id in user_ids
    }


def total_progress(values: list[Progress]) -> Progress:
    total = sum(value.total for value in values)
    confirmed = sum(value.confirmed for value in values)
    return Progress(
        total=total,
        confirmed=confirmed,
        overdue=sum(value.overdue for value in values),
        issues=sum(value.issues for value in values),
        percent=round(confirmed / total * 100) if total else 0,
    )
