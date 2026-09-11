from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..access import visible_user_ids
from ..db import get_db
from ..deps import check_review, check_view, current_user
from ..models import Issue, Link, Meeting, MeetingSkill, PlanItem, User
from ..schemas import (
    IssueIn,
    IssueOut,
    LinkIn,
    MarkIn,
    MarkOut,
    MeetingBrief,
    MeetingIn,
    MeetingOut,
    MeetingUpdate,
)

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def issue_out(issue: Issue) -> IssueOut:
    data = IssueOut.model_validate(issue)
    data.skill_name = issue.plan_item.skill.name if issue.plan_item else None
    data.employee_name = issue.employee.full_name if issue.employee else ""
    return data


def meeting_out(meeting: Meeting) -> MeetingOut:
    data = MeetingOut.model_validate(meeting)
    for mark, source in zip(data.marks, meeting.marks):
        mark.skill_name = source.plan_item.skill.name
    data.issues = [issue_out(issue) for issue in meeting.issues]
    return data


def get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(404, "Встреча не найдена")
    return meeting


@router.get("", response_model=list[MeetingBrief])
def list_meetings(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    query = select(Meeting).order_by(Meeting.scheduled_at.desc())
    if employee_id is not None:
        check_view(db, actor, employee_id)
        query = query.where(Meeting.employee_id == employee_id)
    else:
        allowed = visible_user_ids(db, actor)
        if allowed is not None:
            query = query.where(
                or_(Meeting.employee_id.in_(allowed or {-1}), Meeting.reviewer_id == actor.id)
            )
    return db.scalars(query).all()


@router.post("", response_model=MeetingOut, status_code=201)
def create_meeting(
    data: MeetingIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    check_review(db, actor, data.employee_id)
    meeting = Meeting(
        employee_id=data.employee_id,
        reviewer_id=actor.id,
        scheduled_at=data.scheduled_at,
        title=data.title or "PR-встреча",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting_out(meeting)


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    meeting = get_meeting_or_404(db, meeting_id)
    if meeting.reviewer_id != actor.id:
        check_view(db, actor, meeting.employee_id)
    return meeting_out(meeting)


@router.patch("/{meeting_id}", response_model=MeetingOut)
def edit_meeting(
    meeting_id: int,
    data: MeetingUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    meeting = get_meeting_or_404(db, meeting_id)
    check_review(db, actor, meeting.employee_id)
    if data.scheduled_at is not None:
        meeting.scheduled_at = data.scheduled_at
    if data.title is not None:
        meeting.title = data.title
    if data.notes_md is not None:
        meeting.notes_md = data.notes_md
    if data.is_held is not None:
        meeting.held_at = datetime.now(timezone.utc) if data.is_held else None
    db.commit()
    db.refresh(meeting)
    return meeting_out(meeting)


@router.delete("/{meeting_id}", status_code=204, response_model=None)
def delete_meeting(
    meeting_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)
) -> None:
    meeting = get_meeting_or_404(db, meeting_id)
    check_review(db, actor, meeting.employee_id)
    # Снимаем зачёты, которые поставила эта встреча, иначе прогресс останется завышенным.
    for item in db.scalars(
        select(PlanItem).where(PlanItem.confirmed_meeting_id == meeting.id)
    ).all():
        item.is_confirmed = False
        item.confirmed_at = None
        item.confirmed_meeting_id = None
    db.delete(meeting)
    db.commit()


@router.put("/{meeting_id}/marks", response_model=MeetingOut)
def set_mark(
    meeting_id: int,
    data: MarkIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    """Отметить скилл на встрече: обсуждали или зачли."""
    meeting = get_meeting_or_404(db, meeting_id)
    check_review(db, actor, meeting.employee_id)

    item = db.get(PlanItem, data.plan_item_id)
    if item is None or item.plan.user_id != meeting.employee_id:
        raise HTTPException(400, "Этого скилла нет в плане сотрудника")

    mark = db.scalar(
        select(MeetingSkill).where(
            MeetingSkill.meeting_id == meeting.id,
            MeetingSkill.plan_item_id == data.plan_item_id,
        )
    )
    if mark is None:
        mark = MeetingSkill(meeting_id=meeting.id, plan_item_id=data.plan_item_id)
        db.add(mark)
    mark.is_confirmed = data.is_confirmed
    mark.comment = data.comment

    if data.is_confirmed:
        item.is_confirmed = True
        item.confirmed_at = (meeting.held_at or meeting.scheduled_at).date()
        item.confirmed_meeting_id = meeting.id
    elif item.confirmed_meeting_id == meeting.id:
        item.is_confirmed = False
        item.confirmed_at = None
        item.confirmed_meeting_id = None

    db.commit()
    db.refresh(meeting)
    return meeting_out(meeting)


@router.delete("/{meeting_id}/marks/{mark_id}", response_model=MeetingOut)
def delete_mark(
    meeting_id: int,
    mark_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    meeting = get_meeting_or_404(db, meeting_id)
    check_review(db, actor, meeting.employee_id)
    mark = db.get(MeetingSkill, mark_id)
    if mark is None or mark.meeting_id != meeting.id:
        raise HTTPException(404, "Отметка не найдена")
    item = mark.plan_item
    if item.confirmed_meeting_id == meeting.id:
        item.is_confirmed = False
        item.confirmed_at = None
        item.confirmed_meeting_id = None
    db.delete(mark)
    db.commit()
    db.refresh(meeting)
    return meeting_out(meeting)


@router.post("/{meeting_id}/links", response_model=MeetingOut, status_code=201)
def add_link(
    meeting_id: int,
    data: LinkIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    meeting = get_meeting_or_404(db, meeting_id)
    check_review(db, actor, meeting.employee_id)
    db.add(Link(meeting_id=meeting.id, title=data.title or data.url, url=data.url.strip()))
    db.commit()
    db.refresh(meeting)
    return meeting_out(meeting)


@router.delete("/{meeting_id}/links/{link_id}", response_model=MeetingOut)
def delete_link(
    meeting_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    meeting = get_meeting_or_404(db, meeting_id)
    check_review(db, actor, meeting.employee_id)
    link = db.get(Link, link_id)
    if link is None or link.meeting_id != meeting.id:
        raise HTTPException(404, "Ссылка не найдена")
    db.delete(link)
    db.commit()
    db.refresh(meeting)
    return meeting_out(meeting)


# --- Проблемы -------------------------------------------------------------

issues_router = APIRouter(prefix="/api/issues", tags=["issues"])


@issues_router.get("", response_model=list[IssueOut])
def list_issues(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    query = select(Issue).order_by(Issue.created_at.desc())
    if employee_id is not None:
        check_view(db, actor, employee_id)
        query = query.where(Issue.employee_id == employee_id)
    else:
        allowed = visible_user_ids(db, actor)
        if allowed is not None:
            query = query.where(Issue.employee_id.in_(allowed or {-1}))
    return [issue_out(issue) for issue in db.scalars(query).all()]


@issues_router.post("/{employee_id}", response_model=IssueOut, status_code=201)
def add_issue(
    employee_id: int,
    data: IssueIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    check_review(db, actor, employee_id)
    issue = Issue(
        employee_id=employee_id,
        meeting_id=data.meeting_id,
        plan_item_id=data.plan_item_id,
        comment=data.comment,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue_out(issue)


@issues_router.post("/{issue_id}/resolve", response_model=IssueOut)
def resolve_issue(
    issue_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(404, "Проблема не найдена")
    check_review(db, actor, issue.employee_id)
    issue.is_resolved = True
    db.commit()
    db.refresh(issue)
    return issue_out(issue)
