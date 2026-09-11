from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import department_path, manager_of, subordinate_ids
from ..db import get_db
from ..deps import current_user
from ..models import Company, User
from ..schemas import (
    ChangePassword,
    CompanyBrief,
    CompanyOut,
    LoginRequest,
    Me,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/companies", response_model=list[CompanyBrief])
def companies(db: Session = Depends(get_db)) -> list[CompanyBrief]:
    """Список компаний для выбора при регистрации. Доступен без входа."""
    rows = db.execute(
        select(Company, func.count(User.id))
        .outerjoin(User, User.company_id == Company.id)
        .group_by(Company.id)
        .order_by(Company.name)
    ).all()
    return [
        CompanyBrief(id=company.id, name=company.name, employees=count) for company, count in rows
    ]


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Регистрация.

    ``mode=create`` — человек заводит свою компанию и становится её
    администратором: дальше он наполняет справочник, строит структуру и
    распределяет сотрудников.

    ``mode=join`` — человек вступает в существующую компанию обычным
    сотрудником. Пока администратор не добавил его в подразделение, он видит
    только себя.
    """
    email = data.email.strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(409, "Пользователь с такой почтой уже зарегистрирован")

    if data.mode == "create":
        name = data.company_name.strip()
        if not name:
            raise HTTPException(400, "Укажите название компании")
        # lower() в SQLite не трогает кириллицу, поэтому сравниваем в Python.
        existing = {c.name.strip().lower() for c in db.scalars(select(Company)).all()}
        if name.lower() in existing:
            raise HTTPException(409, "Компания с таким названием уже есть")
        company = Company(name=name)
        db.add(company)
        db.flush()
        is_admin = True
    else:
        company = db.get(Company, data.company_id) if data.company_id else None
        if company is None:
            raise HTTPException(400, "Выберите компанию, к которой хотите присоединиться")
        is_admin = False

    user = User(
        email=email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        position=data.position.strip(),
        is_admin=is_admin,
        company_id=company.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.strip().lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return TokenResponse(access_token=create_token(user.id))


@router.get("/me", response_model=Me)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Me:
    manager = manager_of(db, user)
    data = UserOut.model_validate(user)
    data.department_path = department_path(db, user.company_id, user.department_id)
    data.manager_name = manager.full_name if manager else None
    data.relation = "self"
    company = db.get(Company, user.company_id)
    return Me(
        user=data,
        is_admin=user.is_admin,
        subordinates=len(subordinate_ids(db, user)),
        company=CompanyOut.model_validate(company),
    )


@router.post("/change-password", status_code=204, response_model=None)
def change_password(
    data: ChangePassword,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Текущий пароль указан неверно")
    user.password_hash = hash_password(data.new_password)
    db.commit()
