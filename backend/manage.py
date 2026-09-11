"""Команды для обслуживания стенда.

Нужны, когда до интерфейса не добраться: забыли пароль владельца, надо выдать
права администратора второму человеку или посмотреть, кто вообще заведён.

Запуск из папки backend:

    PYTHONPATH=. python manage.py users
    PYTHONPATH=. python manage.py make-admin ivanov@company.ru
    PYTHONPATH=. python manage.py set-password ivanov@company.ru новыйпароль
"""

from __future__ import annotations

import sys

from sqlalchemy import func, select

from app.db import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password


def find(db, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def list_users() -> None:
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        if not users:
            print("Пользователей нет. Первый, кто зарегистрируется, станет администратором.")
            return
        for user in users:
            role = "администратор" if user.is_admin else "сотрудник"
            department = user.department.name if user.department else "без подразделения"
            print(f"{user.id:>3}  {user.email:<32} {user.full_name:<28} {role:<14} {department}")


def make_admin(email: str) -> None:
    with SessionLocal() as db:
        user = find(db, email)
        if user is None:
            print(f"Пользователь {email} не найден")
            sys.exit(1)
        user.is_admin = True
        db.commit()
        print(f"{user.full_name} ({user.email}) теперь администратор")


def set_password(email: str, password: str) -> None:
    if len(password) < 6:
        print("Пароль должен быть не короче 6 символов")
        sys.exit(1)
    with SessionLocal() as db:
        user = find(db, email)
        if user is None:
            print(f"Пользователь {email} не найден")
            sys.exit(1)
        user.password_hash = hash_password(password)
        db.commit()
        print(f"Пароль для {user.email} изменён")


def main() -> None:
    # В консоли Windows по умолчанию не UTF-8, и кириллица превращается в кашу.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    Base.metadata.create_all(bind=engine)
    args = sys.argv[1:]
    command = args[0] if args else ""

    if command == "users":
        list_users()
    elif command == "make-admin" and len(args) == 2:
        make_admin(args[1])
    elif command == "set-password" and len(args) == 3:
        set_password(args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
