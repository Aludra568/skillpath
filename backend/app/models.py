from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Direction(Base):
    """Направление: BACK, FRONT, QA."""

    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))


class Skill(Base):
    """Навык из справочника."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    direction_id: Mapped[int] = mapped_column(ForeignKey("directions.id", ondelete="CASCADE"))

    direction: Mapped[Direction] = relationship()


class Department(Base):
    """Подразделение. Вложенность любой глубины через parent_id."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True
    )
    head_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    head: Mapped[User | None] = relationship(foreign_keys=[head_id])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(256))
    position: Mapped[str] = mapped_column(String(160), default="")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    direction_id: Mapped[int | None] = mapped_column(
        ForeignKey("directions.id", ondelete="SET NULL"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    direction: Mapped[Direction | None] = relationship()
    department: Mapped[Department | None] = relationship(foreign_keys=[department_id])


class Plan(Base):
    """Годовой план обучения сотрудника."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer)

    items: Mapped[list[PlanItem]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.target_date"
    )


class PlanItem(Base):
    """Скилл в плане и дата, к которой его надо подтвердить."""

    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"))
    target_date: Mapped[date] = mapped_column(Date)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Встреча, на которой скилл зачли. Нужна, чтобы при отмене отметки снять зачёт.
    confirmed_meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True
    )

    plan: Mapped[Plan] = relationship(back_populates="items")
    skill: Mapped[Skill] = relationship()


class Meeting(Base):
    """PR-встреча один на один."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    notes_md: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped[User] = relationship(foreign_keys=[employee_id])
    reviewer: Mapped[User] = relationship(foreign_keys=[reviewer_id])
    marks: Mapped[list[MeetingSkill]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    links: Mapped[list[Link]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    issues: Mapped[list[Issue]] = relationship(back_populates="meeting")


class MeetingSkill(Base):
    """Скилл, который обсуждали на встрече. is_confirmed = зачли."""

    __tablename__ = "meeting_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    plan_item_id: Mapped[int] = mapped_column(ForeignKey("plan_items.id", ondelete="CASCADE"))
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str] = mapped_column(Text, default="")

    meeting: Mapped[Meeting] = relationship(back_populates="marks")
    plan_item: Mapped[PlanItem] = relationship()


class Link(Base):
    """Ссылка, приложенная к встрече."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str] = mapped_column(Text)

    meeting: Mapped[Meeting] = relationship(back_populates="links")


class Issue(Base):
    """Проблема по скиллу или по сотруднику в целом."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True
    )
    plan_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_items.id", ondelete="CASCADE"), nullable=True
    )
    comment: Mapped[str] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[User] = relationship(foreign_keys=[employee_id])
    meeting: Mapped[Meeting | None] = relationship(back_populates="issues")
    plan_item: Mapped[PlanItem | None] = relationship()
