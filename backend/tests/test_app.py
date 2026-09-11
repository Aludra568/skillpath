"""Тесты: регистрация, права и основной сценарий.

Компания собирается прямо в тестах через API — так же, как её собирает
настоящий пользователь. Демо-данных в проекте нет.

Запуск из папки backend:  PYTHONPATH=. python tests/test_app.py
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="skillpath-test-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(os.environ['DATA_DIR']).as_posix()}/test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

PASSWORD = "test12345"


def register(email: str, name: str, position: str = "") -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": name, "password": PASSWORD, "position": position},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def login(email: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def user_id(headers: dict[str, str]) -> int:
    return client.get("/api/auth/me", headers=headers).json()["user"]["id"]


# --- Сборка компании: ровно те шаги, что делает живой администратор ---------

assert client.get("/api/auth/needs-setup").json()["empty"] is True

owner = register("owner@company.ru", "Ольга Владелец", "Директор")
owner_id = user_id(owner)

# Направления и скиллы.
back = client.post("/api/directions", headers=owner, json={"code": "BACK", "name": "Backend"}).json()
front = client.post(
    "/api/directions", headers=owner, json={"code": "FRONT", "name": "Frontend"}
).json()
skills = [
    client.post(
        "/api/skills",
        headers=owner,
        json={"name": name, "description": "", "direction_id": back["id"]},
    ).json()
    for name in ("PostgreSQL", "Асинхронность", "REST API", "Очереди")
]
front_skill = client.post(
    "/api/skills", headers=owner, json={"name": "React", "description": "", "direction_id": front["id"]}
).json()

# Сотрудники регистрируются сами.
lead = register("lead@company.ru", "Павел Руководитель", "Руководитель backend")
sub_lead = register("sublead@company.ru", "Дмитрий Тимлид", "Тимлид платформы")
dev = register("dev@company.ru", "Артём Разработчик", "Backend-разработчик")
other = register("other@company.ru", "Иван Фронтендер", "Frontend-разработчик")

lead_id = user_id(lead)
sub_lead_id = user_id(sub_lead)
dev_id = user_id(dev)
other_id = user_id(other)

# Администратор строит структуру и распределяет людей.
company = client.post(
    "/api/departments", headers=owner, json={"name": "Компания", "head_id": owner_id}
).json()
backend_dept = client.post(
    "/api/departments",
    headers=owner,
    json={"name": "Backend", "parent_id": company["id"], "head_id": lead_id},
).json()
platform_dept = client.post(
    "/api/departments",
    headers=owner,
    json={"name": "Платформа", "parent_id": backend_dept["id"], "head_id": sub_lead_id},
).json()
frontend_dept = client.post(
    "/api/departments", headers=owner, json={"name": "Frontend", "parent_id": company["id"]}
).json()


def assign(target_id: int, email: str, name: str, position: str, dept: int, direction: int) -> None:
    response = client.patch(
        f"/api/users/{target_id}",
        headers=owner,
        json={
            "email": email,
            "full_name": name,
            "position": position,
            "is_admin": False,
            "department_id": dept,
            "direction_id": direction,
        },
    )
    assert response.status_code == 200, response.text


assign(lead_id, "lead@company.ru", "Павел Руководитель", "Рук. backend", backend_dept["id"], back["id"])
assign(
    sub_lead_id, "sublead@company.ru", "Дмитрий Тимлид", "Тимлид", platform_dept["id"], back["id"]
)
assign(dev_id, "dev@company.ru", "Артём Разработчик", "Разработчик", backend_dept["id"], back["id"])
assign(
    other_id, "other@company.ru", "Иван Фронтендер", "Фронтендер", frontend_dept["id"], front["id"]
)

# Владельца ставим в корневое подразделение, права администратора сохраняем.
client.patch(
    f"/api/users/{owner_id}",
    headers=owner,
    json={
        "email": "owner@company.ru",
        "full_name": "Ольга Владелец",
        "position": "Директор",
        "is_admin": True,
        "department_id": company["id"],
        "direction_id": back["id"],
    },
)


# --- Тесты -----------------------------------------------------------------


def test_first_registered_is_admin():
    assert client.get("/api/auth/me", headers=owner).json()["is_admin"] is True
    assert client.get("/api/auth/needs-setup").json()["empty"] is False


def test_next_users_are_not_admins_and_have_no_department():
    fresh = register("fresh@company.ru", "Новый Сотрудник")
    me = client.get("/api/auth/me", headers=fresh).json()
    assert me["is_admin"] is False
    assert me["user"]["department"] is None
    # Пока не распределён — видит только себя и никаких подразделений.
    assert len(client.get("/api/users", headers=fresh).json()) == 1
    assert client.get("/api/analytics/departments", headers=fresh).json() == []


def test_duplicate_email_is_rejected():
    response = client.post(
        "/api/auth/register",
        json={"email": "dev@company.ru", "full_name": "Двойник", "password": PASSWORD},
    )
    assert response.status_code == 409


def test_short_password_is_rejected():
    response = client.post(
        "/api/auth/register",
        json={"email": "short@company.ru", "full_name": "Кто-то", "password": "123"},
    )
    assert response.status_code == 422


def test_wrong_password():
    assert client.post(
        "/api/auth/login", json={"email": "owner@company.ru", "password": "нет"}
    ).status_code == 401


def test_change_own_password():
    headers = register("pwd@company.ru", "Смена Пароля")
    assert client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "неверный", "new_password": "newpass123"},
    ).status_code == 400

    assert client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "newpass123"},
    ).status_code == 204

    assert client.post(
        "/api/auth/login", json={"email": "pwd@company.ru", "password": "newpass123"}
    ).status_code == 200


def test_role_depends_on_tree():
    """Руководитель ведёт PR подчинённых, но свой PR ведёт не он."""
    users = {u["id"]: u for u in client.get("/api/users", headers=lead).json()}
    assert users[dev_id]["relation"] == "manager"
    assert users[lead_id]["relation"] == "self"

    # Для владельца тот же руководитель — подчинённый.
    from_owner = client.get(f"/api/users/{lead_id}", headers=owner).json()
    assert from_owner["relation"] == "admin"


def test_manager_sees_nested_department():
    names = {u["full_name"] for u in client.get("/api/users", headers=lead).json()}
    assert "Дмитрий Тимлид" in names  # вложенная «Платформа»
    assert "Иван Фронтендер" not in names  # соседний отдел


def test_foreign_employee_is_forbidden():
    assert client.get(f"/api/users/{other_id}", headers=lead).status_code == 403


def test_employee_cannot_create_meeting():
    response = client.post(
        "/api/meetings",
        headers=dev,
        json={"employee_id": dev_id, "scheduled_at": datetime.now(timezone.utc).isoformat()},
    )
    assert response.status_code == 403


def test_main_scenario():
    """План -> встреча -> зачёт -> прогресс, и откат зачёта."""
    plan = client.post(f"/api/users/{dev_id}/plan", headers=lead).json()
    assert plan["items"] == []

    for skill, month in zip(skills[:2], (6, 9)):
        client.post(
            f"/api/users/{dev_id}/plan/items",
            headers=lead,
            json={"skill_id": skill["id"], "target_date": f"{date.today().year}-{month:02d}-01"},
        )

    plan = client.get(f"/api/users/{dev_id}/plan", headers=lead).json()
    assert plan["progress"]["total"] == 2 and plan["progress"]["confirmed"] == 0
    item = plan["items"][0]

    meeting = client.post(
        "/api/meetings",
        headers=lead,
        json={
            "employee_id": dev_id,
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "title": "PR-встреча",
        },
    ).json()

    client.patch(f"/api/meetings/{meeting['id']}", headers=lead, json={"notes_md": "## Итоги"})
    marked = client.put(
        f"/api/meetings/{meeting['id']}/marks",
        headers=lead,
        json={"plan_item_id": item["id"], "is_confirmed": True, "comment": "зачтено"},
    )
    assert marked.status_code == 200, marked.text

    client.post(
        f"/api/meetings/{meeting['id']}/links",
        headers=lead,
        json={"title": "Запись", "url": "https://example.com"},
    )
    issue = client.post(
        f"/api/issues/{dev_id}",
        headers=lead,
        json={"comment": "Нужен ещё подход", "meeting_id": meeting["id"]},
    )
    assert issue.status_code == 201

    after = client.get(f"/api/users/{dev_id}/plan", headers=lead).json()
    assert after["progress"]["confirmed"] == 1

    stats = client.get(f"/api/analytics/employees/{dev_id}", headers=lead).json()
    assert stats["progress"]["confirmed"] == 1 and len(stats["issues"]) == 1

    mark_id = next(m["id"] for m in marked.json()["marks"] if m["plan_item_id"] == item["id"])
    client.delete(f"/api/meetings/{meeting['id']}/marks/{mark_id}", headers=lead)
    assert client.get(f"/api/users/{dev_id}/plan", headers=lead).json()["progress"]["confirmed"] == 0


def test_catalog_only_for_admin():
    payload = {"name": "Новый скилл", "description": "", "direction_id": back["id"]}
    assert client.post("/api/skills", headers=lead, json=payload).status_code == 403
    created = client.post("/api/skills", headers=owner, json=payload)
    assert created.status_code == 201
    client.delete(f"/api/skills/{created.json()['id']}", headers=owner)


def test_department_cannot_move_into_itself():
    response = client.patch(
        f"/api/departments/{company['id']}",
        headers=owner,
        json={"name": "Компания", "parent_id": backend_dept["id"], "head_id": owner_id},
    )
    assert response.status_code == 400


def test_department_stats_and_filters():
    stats = {s["name"]: s for s in client.get("/api/analytics/departments", headers=lead).json()}
    assert set(stats) == {"Backend", "Платформа"}
    assert stats["Backend"]["employees"] >= 3  # вложенная «Платформа» учтена

    filtered = client.get("/api/users", headers=owner, params={"direction_id": front["id"]}).json()
    assert filtered and all(u["direction"]["code"] == "FRONT" for u in filtered)
    assert front_skill["direction_id"] == front["id"]


def test_events_have_meetings_and_deadlines():
    # Готовим свои данные: срок по скиллу и встречу впереди.
    target = date.today() + timedelta(days=20)
    if target.year != date.today().year:
        target = date(date.today().year, 12, 31)

    client.post(f"/api/users/{sub_lead_id}/plan", headers=lead)
    client.post(
        f"/api/users/{sub_lead_id}/plan/items",
        headers=lead,
        json={"skill_id": skills[2]["id"], "target_date": target.isoformat()},
    )
    client.post(
        "/api/meetings",
        headers=lead,
        json={
            "employee_id": sub_lead_id,
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "title": "PR-встреча",
        },
    )

    events = client.get("/api/events", headers=lead, params={"days": 45}).json()
    assert {e["kind"] for e in events} == {"meeting", "deadline"}
    assert events == sorted(events, key=lambda e: e["date"])


if __name__ == "__main__":
    import sys
    import traceback

    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print("OK  ", name)
            except Exception:
                failed += 1
                print("FAIL", name)
                traceback.print_exc()
    sys.exit(1 if failed else 0)
