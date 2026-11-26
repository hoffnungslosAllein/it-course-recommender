"""Тесты загрузки конфигурации."""

import pytest

from skillrec.config import ConfigError, load_config

CONFIG_TEXT = """
paths:
  raw: data/raw
  db: data/db/skillrec.db
  dictionary: data/dictionary

http:
  user_agent: test-agent
  timeout: 30
  retries: 3
  delay: 0.5

hh:
  base_url: https://api.hh.ru
  token_url: https://api.hh.ru/token
  area: 113
  per_page: 100
  max_pages: 20

stepik:
  base_url: https://stepik.org
  per_page: 20
  language: ru

roles:
  - id: backend
    title: Backend
    queries:
      - python
  - id: frontend
    title: Frontend
    queries:
      - javascript
"""


def write_config(tmp_path, text=CONFIG_TEXT):
    """Записать временный config.yaml и вернуть путь к нему."""
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_reads_roles(tmp_path):
    config = load_config(write_config(tmp_path))
    assert len(config["roles"]) == 2
    assert config["roles"][0]["id"] == "backend"


def test_paths_are_relative_to_config(tmp_path):
    config = load_config(write_config(tmp_path))
    assert config["paths"]["db"] == tmp_path / "data" / "db" / "skillrec.db"
    assert config["paths"]["db"].is_absolute()


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "no_such_config.yaml")


def test_bad_per_page(tmp_path):
    text = CONFIG_TEXT.replace("per_page: 100", "per_page: 500")
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, text))


def test_duplicate_role_ids(tmp_path):
    text = CONFIG_TEXT.replace("id: frontend", "id: backend")
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, text))


def test_empty_queries(tmp_path):
    text = CONFIG_TEXT.replace("      - javascript\n", "")
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, text))
