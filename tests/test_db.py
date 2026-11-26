"""Тесты создания базы данных."""

import sqlite3

import pytest

from skillrec.db import DbError, connect, init_db


def test_init_db_creates_tables(tmp_path):
    result = init_db(tmp_path / "test.db")
    assert result["fresh"] is True
    assert result["version"] == 1
    assert len(result["tables"]) == 13
    assert "vacancies" in result["tables"]
    assert "courses" in result["tables"]


def test_init_db_twice_does_not_fail(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    result = init_db(db_path)
    assert result["fresh"] is False
    assert len(result["tables"]) == 13


def test_force_recreates_database(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = connect(db_path)
    conn.execute("INSERT INTO roles (id, title) VALUES ('test', 'Test')")
    conn.commit()
    conn.close()

    result = init_db(db_path, force=True)
    assert result["fresh"] is True

    conn = connect(db_path)
    count = conn.execute("SELECT count(*) FROM roles").fetchone()[0]
    conn.close()
    assert count == 0


def test_foreign_keys_are_enabled(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO vacancies (source_id, role_id, name) "
            "VALUES ('1', 'no_such_role', 'Test')"
        )
    conn.close()


def test_version_mismatch_is_reported(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = connect(db_path)
    conn.execute("PRAGMA user_version = 99")
    conn.commit()
    conn.close()

    with pytest.raises(DbError):
        init_db(db_path)
