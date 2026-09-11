"""Доводка схемы при старте.

Схема создаётся через create_all, миграций как таковых нет. Но когда появились
компании, у уже работающих стендов в таблицах не было колонки company_id —
здесь мы добавляем её и переносим существующие данные в одну компанию, чтобы
не терять то, что люди успели завести.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).all()
    return {row[1] for row in rows}


def ensure_company_columns(engine: Engine) -> None:
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    with engine.begin() as conn:
        tables = {
            row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        }
        if "users" not in tables or "companies" not in tables:
            return

        needs = [t for t in ("users", "departments", "directions") if "company_id" not in _columns(conn, t)]
        if not needs:
            return

        # Всё, что было заведено до появления компаний, складываем в одну.
        company_id = conn.execute(text("SELECT id FROM companies ORDER BY id LIMIT 1")).scalar()
        if company_id is None:
            conn.execute(
                text("INSERT INTO companies (name, created_at) VALUES (:n, :d)"),
                {"n": "Моя компания", "d": "2026-01-01 00:00:00"},
            )
            company_id = conn.execute(text("SELECT id FROM companies ORDER BY id LIMIT 1")).scalar()

        for table in needs:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN company_id INTEGER"))
            conn.execute(text(f"UPDATE {table} SET company_id = :c"), {"c": company_id})
            print(f"[миграция] {table}.company_id добавлена, данные перенесены в компанию {company_id}")
