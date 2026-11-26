"""Работа с SQLite: подключение и создание схемы."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 1


class DbError(RuntimeError):
    """Ошибка работы с базой данных."""


def connect(db_path):
    """Открыть базу и включить проверку внешних ключей."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path, force=False):
    """Создать базу и применить schema.sql.

    force=True удаляет старый файл базы и создаёт его заново.
    Возвращает словарь с путём, списком таблиц, версией схемы и признаком
    того, что база создана с нуля.
    """
    db_path = Path(db_path)
    fresh = force or not db_path.exists()

    if force:
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)

    conn = connect(db_path)
    try:
        version = get_schema_version(conn)

        if version not in (0, SCHEMA_VERSION):
            raise DbError(
                f"база {db_path} имеет версию схемы {version}, ожидается {SCHEMA_VERSION}; "
                "пересоздайте её командой init-db --force"
            )

        try:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        except sqlite3.Error as exc:
            raise DbError(f"не удалось применить схему: {exc}") from exc

        return {
            "path": db_path,
            "tables": list_tables(conn),
            "version": get_schema_version(conn),
            "fresh": fresh,
        }
    finally:
        conn.close()


def list_tables(conn):
    """Вернуть имена таблиц базы."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def get_schema_version(conn):
    """Вернуть версию схемы из PRAGMA user_version."""
    return conn.execute("PRAGMA user_version").fetchone()[0]
