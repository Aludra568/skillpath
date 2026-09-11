from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def utc_dates(self):
        """SQLite отдаёт время без часового пояса, помечаем его как UTC.

        Иначе браузер считает такую дату локальной и показывает разное время
        в разных местах интерфейса.
        """
        for name, value in self.__dict__.items():
            if isinstance(value, datetime) and value.tzinfo is None:
                setattr(self, name, value.replace(tzinfo=timezone.utc))
        return self


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=6, max_length=128)
    position: str = ""


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str


# --- Справочник -----------------------------------------------------------


class DirectionIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)


class DirectionOut(ORMModel):
    id: int
    code: str
    name: str


class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    direction_id: int


class SkillOut(ORMModel):
    id: int
    name: str
    description: str
    direction_id: int
    direction: DirectionOut | None = None


# --- Подразделения --------------------------------------------------------


class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parent_id: int | None = None
    head_id: int | None = None


class DepartmentOut(ORMModel):
    id: int
    name: str
    parent_id: int | None
    head_id: int | None


class UserBrief(ORMModel):
    id: int
    full_name: str
    position: str = ""


class DepartmentNode(DepartmentOut):
    head_name: str | None = None
    members: list[UserBrief] = []
    children: list[DepartmentNode] = []


DepartmentNode.model_rebuild()


# --- Пользователи ---------------------------------------------------------


class UserIn(BaseModel):
    email: str
    full_name: str = Field(min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    position: str = ""
    is_admin: bool = False
    direction_id: int | None = None
    department_id: int | None = None


class Progress(BaseModel):
    total: int = 0
    confirmed: int = 0
    overdue: int = 0
    issues: int = 0
    percent: int = 0


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    position: str
    is_admin: bool
    direction: DirectionOut | None = None
    department: DepartmentOut | None = None
    department_path: list[str] = []
    manager_name: str | None = None
    relation: str = "none"
    progress: Progress = Progress()


class Me(BaseModel):
    user: UserOut
    is_admin: bool
    subordinates: int


# --- План -----------------------------------------------------------------


class PlanItemIn(BaseModel):
    skill_id: int
    target_date: date


class PlanItemOut(ORMModel):
    id: int
    skill: SkillOut
    target_date: date
    is_confirmed: bool
    confirmed_at: date | None
    is_overdue: bool = False


class PlanOut(BaseModel):
    id: int
    year: int
    items: list[PlanItemOut] = []
    progress: Progress = Progress()


# --- Встречи --------------------------------------------------------------


class MeetingIn(BaseModel):
    employee_id: int
    scheduled_at: datetime
    title: str = ""


class MeetingUpdate(BaseModel):
    scheduled_at: datetime | None = None
    title: str | None = None
    notes_md: str | None = None
    is_held: bool | None = None


class MarkIn(BaseModel):
    plan_item_id: int
    is_confirmed: bool = False
    comment: str = ""


class MarkOut(ORMModel):
    id: int
    plan_item_id: int
    is_confirmed: bool
    comment: str
    skill_name: str = ""


class LinkIn(BaseModel):
    title: str = ""
    url: str = Field(min_length=1)


class LinkOut(ORMModel):
    id: int
    title: str
    url: str


class IssueIn(BaseModel):
    comment: str = Field(min_length=1)
    plan_item_id: int | None = None
    meeting_id: int | None = None


class IssueOut(ORMModel):
    id: int
    employee_id: int
    meeting_id: int | None
    comment: str
    is_resolved: bool
    created_at: datetime
    skill_name: str | None = None
    employee_name: str = ""


class MeetingOut(ORMModel):
    id: int
    employee: UserBrief
    reviewer: UserBrief
    scheduled_at: datetime
    held_at: datetime | None
    title: str
    notes_md: str
    marks: list[MarkOut] = []
    links: list[LinkOut] = []
    issues: list[IssueOut] = []


class MeetingBrief(ORMModel):
    id: int
    employee: UserBrief
    reviewer: UserBrief
    scheduled_at: datetime
    held_at: datetime | None
    title: str


# --- Аналитика и события --------------------------------------------------


class DepartmentStats(BaseModel):
    id: int
    name: str
    employees: int
    progress: Progress
    meetings_held: int
    at_risk: list[UserOut] = []


class EmployeeStats(BaseModel):
    progress: Progress
    confirmed: list[PlanItemOut] = []
    overdue: list[PlanItemOut] = []
    issues: list[IssueOut] = []
    meetings_held: int = 0
    next_meeting_at: datetime | None = None


class Event(BaseModel):
    kind: str  # meeting | deadline
    id: int
    date: datetime
    title: str
    employee_id: int
    employee_name: str
    done: bool = False
