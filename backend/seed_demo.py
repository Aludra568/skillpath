"""Наполняет стенд демо-компанией через API: структура, скиллы, планы, встречи.

Нужен, чтобы показать продукт на живых данных, а не на пустых экранах.
Запускать при работающем сервере:

    .venv/bin/python backend/seed_demo.py

Запускать можно повторно — уже созданное не дублируется.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

BASE = "http://127.0.0.1:8000"
PASSWORD = "demo12345"
COMPANY = "Технологии Роста"

sys.stdout.reconfigure(encoding="utf-8")


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print(f"  ! {method} {path} -> {e.code}: {e.read().decode()[:200]}")
        return None


def register(email, name, position, mode="join", company_id=None, company_name=""):
    body = {
        "email": email,
        "full_name": name,
        "password": PASSWORD,
        "position": position,
        "mode": mode,
        "company_name": company_name,
        "company_id": company_id,
    }
    res = call("POST", "/api/auth/register", body)
    if res is None:
        res = call("POST", "/api/auth/login", {"email": email, "password": PASSWORD})
    return res["access_token"] if res else None


# --- компания -------------------------------------------------------------

companies = call("GET", "/api/auth/companies") or []
existing = next((c for c in companies if c["name"] == COMPANY), None)
if existing:
    print(f"Компания «{COMPANY}» уже есть, вхожу владельцем")
    owner = call("POST", "/api/auth/login", {"email": "volkov@rost.dev", "password": PASSWORD})
    owner = owner["access_token"] if owner else None
    company_id = existing["id"]
else:
    owner = register("volkov@rost.dev", "Игорь Волков", "Директор по разработке", "create", company_name=COMPANY)
    company_id = call("GET", "/api/auth/me", token=owner)["company"]["id"]
    print(f"Создана компания «{COMPANY}» (id {company_id})")

if not owner:
    print("Не удалось войти владельцем")
    sys.exit(1)

me = call("GET", "/api/auth/me", token=owner)
owner_id = me["user"]["id"]

# --- справочник -----------------------------------------------------------

directions = {d["code"]: d for d in call("GET", "/api/directions", token=owner) or []}
for code, name in [("BACK", "Backend-разработка"), ("FRONT", "Frontend-разработка"), ("QA", "Тестирование")]:
    if code not in directions:
        d = call("POST", "/api/directions", {"code": code, "name": name}, owner)
        if d:
            directions[code] = d
print("Направления:", ", ".join(directions))

SKILLS = {
    "BACK": ["PostgreSQL: индексы и планы запросов", "Асинхронность в Python", "Проектирование REST API",
             "Очереди сообщений", "Кеширование", "Логи и метрики сервиса"],
    "FRONT": ["React: производительность рендера", "TypeScript: продвинутые типы",
              "Доступность интерфейсов", "Сборка и бандлинг"],
    "QA": ["Автотесты API", "Нагрузочное тестирование", "Тест-дизайн"],
}

skills = {s["name"]: s for s in call("GET", "/api/skills", token=owner) or []}
for code, names in SKILLS.items():
    for name in names:
        if name not in skills:
            s = call("POST", "/api/skills", {"name": name, "description": "", "direction_id": directions[code]["id"]}, owner)
            if s:
                skills[name] = s
print("Скиллов в справочнике:", len(skills))

# --- сотрудники -----------------------------------------------------------

PEOPLE = [
    ("ershov@rost.dev", "Павел Ершов", "Руководитель backend", "BACK"),
    ("kovalev@rost.dev", "Дмитрий Ковалёв", "Тимлид платформы", "BACK"),
    ("orlov@rost.dev", "Артём Орлов", "Backend-разработчик", "BACK"),
    ("titova@rost.dev", "Светлана Титова", "Backend-разработчик", "BACK"),
    ("mironov@rost.dev", "Кирилл Миронов", "Backend-разработчик", "BACK"),
    ("soloveva@rost.dev", "Марина Соловьёва", "Руководитель frontend", "FRONT"),
    ("gusev@rost.dev", "Иван Гусев", "Frontend-разработчик", "FRONT"),
    ("panova@rost.dev", "Елена Панова", "Frontend-разработчик", "FRONT"),
    ("belova@rost.dev", "Анна Белова", "Руководитель QA", "QA"),
    ("sokolov@rost.dev", "Роман Соколов", "QA-инженер", "QA"),
]

for email, name, position, _ in PEOPLE:
    register(email, name, position, "join", company_id=company_id)

users = {u["full_name"]: u for u in call("GET", "/api/users", token=owner) or []}
print("Сотрудников в компании:", len(users))

# --- структура ------------------------------------------------------------

depts = {d["name"]: d for d in call("GET", "/api/departments", token=owner) or []}


def dept(name, parent=None, head=None):
    if name in depts:
        return depts[name]
    body = {"name": name, "parent_id": parent, "head_id": head}
    d = call("POST", "/api/departments", body, owner)
    if d:
        depts[name] = d
    return d


company_dept = dept("Департамент разработки", None, owner_id)
backend = dept("Отдел Backend", company_dept["id"], users["Павел Ершов"]["id"])
platform = dept("Команда «Платформа»", backend["id"], users["Дмитрий Ковалёв"]["id"])
frontend = dept("Отдел Frontend", company_dept["id"], users["Марина Соловьёва"]["id"])
qa = dept("Отдел QA", company_dept["id"], users["Анна Белова"]["id"])
print("Подразделения:", ", ".join(depts))

PLACES = {
    "Игорь Волков": (company_dept, "BACK"),
    "Павел Ершов": (backend, "BACK"),
    "Артём Орлов": (backend, "BACK"),
    "Светлана Титова": (backend, "BACK"),
    "Дмитрий Ковалёв": (platform, "BACK"),
    "Кирилл Миронов": (platform, "BACK"),
    "Марина Соловьёва": (frontend, "FRONT"),
    "Иван Гусев": (frontend, "FRONT"),
    "Елена Панова": (frontend, "FRONT"),
    "Анна Белова": (qa, "QA"),
    "Роман Соколов": (qa, "QA"),
}

for name, (d, code) in PLACES.items():
    u = users.get(name)
    if not u or (u.get("department") or {}).get("id") == d["id"]:
        continue
    call("PATCH", f"/api/users/{u['id']}", {
        "email": u["email"], "full_name": u["full_name"], "position": u["position"],
        "is_admin": u["is_admin"], "department_id": d["id"], "direction_id": directions[code]["id"],
    }, owner)
print("Сотрудники распределены по подразделениям")

users = {u["full_name"]: u for u in call("GET", "/api/users", token=owner) or []}

# --- планы обучения -------------------------------------------------------

year = date.today().year
today = date.today()


def plan_for(name, rows):
    uid = users[name]["id"]
    plan = call("GET", f"/api/users/{uid}/plan", token=owner)
    if plan is None:
        call("POST", f"/api/users/{uid}/plan", {}, owner)
    for skill_name, target in rows:
        call("POST", f"/api/users/{uid}/plan/items",
             {"skill_id": skills[skill_name]["id"], "target_date": target.isoformat()}, owner)


def d(month, day):
    return date(year, month, day)


plan_for("Артём Орлов", [("PostgreSQL: индексы и планы запросов", d(3, 31)),
                         ("Асинхронность в Python", d(6, 30)),
                         ("Проектирование REST API", d(9, 30)),
                         ("Очереди сообщений", d(12, 15))])
plan_for("Светлана Титова", [("Кеширование", d(5, 31)),
                             ("Логи и метрики сервиса", d(8, 31)),
                             ("Проектирование REST API", d(11, 30))])
plan_for("Кирилл Миронов", [("Очереди сообщений", d(4, 30)),
                            ("Логи и метрики сервиса", today + timedelta(days=9))])
plan_for("Иван Гусев", [("TypeScript: продвинутые типы", d(4, 30)),
                        ("React: производительность рендера", d(8, 15)),
                        ("Доступность интерфейсов", d(11, 30))])
plan_for("Елена Панова", [("Сборка и бандлинг", d(5, 31)), ("Тест-дизайн", d(10, 31))])
plan_for("Роман Соколов", [("Тест-дизайн", d(3, 31)), ("Автотесты API", d(7, 31))])
plan_for("Павел Ершов", [("Очереди сообщений", d(9, 30))])
print("Планы обучения заведены")

# --- встречи --------------------------------------------------------------


def dt(day, hour=11):
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=hour).isoformat()


def meeting(employee, reviewer_token, day, notes, marks, link=None, issue=None):
    uid = users[employee]["id"]
    m = call("POST", "/api/meetings", {"employee_id": uid, "scheduled_at": dt(day), "title": "PR-встреча"}, reviewer_token)
    if not m:
        return None
    call("PATCH", f"/api/meetings/{m['id']}", {"notes_md": notes}, reviewer_token)
    plan = call("GET", f"/api/users/{uid}/plan", token=reviewer_token) or {"items": []}
    by_skill = {i["skill"]["name"]: i for i in plan["items"]}
    for skill_name, confirmed, comment in marks:
        item = by_skill.get(skill_name)
        if item:
            call("PUT", f"/api/meetings/{m['id']}/marks",
                 {"plan_item_id": item["id"], "is_confirmed": confirmed, "comment": comment}, reviewer_token)
    if link:
        call("POST", f"/api/meetings/{m['id']}/links", {"title": link[0], "url": link[1]}, reviewer_token)
    call("PATCH", f"/api/meetings/{m['id']}", {"is_held": True, "held_at": dt(day)}, reviewer_token)
    if issue:
        body = {"comment": issue[0], "meeting_id": m["id"]}
        if issue[1]:
            item = by_skill.get(issue[1])
            if item:
                body["plan_item_id"] = item["id"]
        call("POST", f"/api/issues/{uid}", body, reviewer_token)
    return m


lead = call("POST", "/api/auth/login", {"email": "ershov@rost.dev", "password": PASSWORD})["access_token"]
sub_lead = call("POST", "/api/auth/login", {"email": "kovalev@rost.dev", "password": PASSWORD})["access_token"]
front_lead = call("POST", "/api/auth/login", {"email": "soloveva@rost.dev", "password": PASSWORD})["access_token"]
qa_lead = call("POST", "/api/auth/login", {"email": "belova@rost.dev", "password": PASSWORD})["access_token"]

# Если стенд уже наполняли раньше, поправим датировку проведённых встреч.
for m in call("GET", "/api/meetings", token=owner) or []:
    if m["held_at"] and m["held_at"][:10] != m["scheduled_at"][:10]:
        call("PATCH", f"/api/meetings/{m['id']}", {"held_at": m["scheduled_at"]}, owner)
        print("поправлена дата проведения встречи", m["id"])

existing_meetings = call("GET", "/api/meetings", token=owner) or []
if len(existing_meetings) < 3:
    meeting("Артём Орлов", lead, d(3, 28),
            "## Итоги\n\n- Разобрали план выполнения тяжёлых запросов в отчётах\n"
            "- Артём ускорил выгрузку с 9 секунд до 1.2\n\n### Договорились\n"
            "1. Написать внутренний гайд по индексам\n2. Взять в работу асинхронный клиент",
            [("PostgreSQL: индексы и планы запросов", True, "Показал разбор EXPLAIN на боевом запросе")],
            link=("Гайд по индексам", "https://example.com/wiki/postgres-indexes"))

    meeting("Артём Орлов", lead, d(6, 27),
            "## Асинхронность\n\nПрошли ревью сервиса нотификаций, замеры до и после приложены.",
            [("Асинхронность в Python", True, "Отладил блокирующий вызов в проде"),
             ("Проектирование REST API", False, "Начали разбирать версионирование")])

    meeting("Светлана Титова", lead, d(8, 29),
            "## Логи и метрики\n\nМетрики сервиса завели, алертов пока нет — перенесли на следующий спринт.",
            [("Кеширование", True, "Redis и инвалидация разобраны"),
             ("Логи и метрики сервиса", False, "Не хватило времени на алерты")],
            issue=("Нет алертов и дашборда, плановая дата 31.08 просрочена", "Логи и метрики сервиса"))

    meeting("Кирилл Миронов", sub_lead, d(4, 25),
            "Разобрали гарантии доставки, сделали ретраи с экспоненциальной задержкой.",
            [("Очереди сообщений", True, "Защитил схему ретраев на архкоме")])

    meeting("Иван Гусев", front_lead, d(4, 26),
            "## TypeScript\n\nПеревели формы на строгие типы, убрали any из ядра.",
            [("TypeScript: продвинутые типы", True, "Разобрал generics и сужение типов")])

    meeting("Роман Соколов", qa_lead, d(7, 30),
            "Автотесты покрывают критичный путь оформления заказа.",
            [("Автотесты API", True, "Контрактные тесты в CI")])

    call("POST", f"/api/issues/{users['Иван Гусев']['id']}",
         {"comment": "Иван перегружен продуктовыми задачами, обучение идёт медленнее плана"}, front_lead)
    print("Проведённые встречи и проблемы заведены")

# --- будущие встречи ------------------------------------------------------

upcoming = [("Артём Орлов", lead, 5), ("Светлана Титова", lead, 12),
            ("Кирилл Миронов", sub_lead, 16), ("Иван Гусев", front_lead, 7),
            ("Павел Ершов", owner, 21)]
planned = [m for m in call("GET", "/api/meetings", token=owner) or [] if not m["held_at"]]
if len(planned) < 3:
    for name, token, offset in upcoming:
        call("POST", "/api/meetings",
             {"employee_id": users[name]["id"], "scheduled_at": dt(today + timedelta(days=offset), 12),
              "title": "PR-встреча"}, token)
    print("Будущие встречи назначены")

print()
print("=== ГОТОВО ===")
print(f"Компания: {COMPANY}")
print(f"Владелец/админ: volkov@rost.dev / {PASSWORD}")
print(f"Руководитель backend: ershov@rost.dev / {PASSWORD}")
print(f"Разработчик: orlov@rost.dev / {PASSWORD}")
stats = call("GET", "/api/analytics/departments", token=owner) or []
for s in stats:
    print(f"  {s['name']}: сотрудников {s['employees']}, план {s['progress']['percent']}%, "
          f"просрочек {s['progress']['overdue']}, проблем {s['progress']['issues']}")
