"""Загрузка config.yaml и проверка обязательных полей."""

from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = "config.yaml"

# Какие поля обязательны в каждом разделе.
REQUIRED_FIELDS = {
    "paths": ("raw", "db", "dictionary"),
    "http": ("user_agent", "timeout", "retries", "delay"),
    "hh": ("base_url", "token_url", "area", "per_page", "max_pages"),
    "stepik": ("base_url", "per_page", "language"),
}


class ConfigError(ValueError):
    """Ошибка в конфигурации."""


def load_config(path=None):
    """Прочитать config.yaml, проверить поля и вернуть словарь.

    Пути из раздела paths становятся абсолютными: они считаются
    от каталога, в котором лежит config.yaml.
    """
    config_path = Path(path or DEFAULT_CONFIG_PATH).resolve()

    if not config_path.exists():
        raise ConfigError(f"файл конфигурации не найден: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"не удалось разобрать {config_path.name}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"{config_path.name}: ожидался набор разделов")

    check_config(data)

    for key in ("raw", "db", "dictionary"):
        data["paths"][key] = config_path.parent / data["paths"][key]

    return data


def check_config(data):
    """Проверить разделы, обязательные поля и список ролей."""
    for section, fields in REQUIRED_FIELDS.items():
        if not isinstance(data.get(section), dict):
            raise ConfigError(f"отсутствует раздел {section!r}")

        for field in fields:
            if field not in data[section]:
                raise ConfigError(f"{section}: не задано поле {field!r}")

    per_page = data["hh"]["per_page"]
    if not isinstance(per_page, int) or not 1 <= per_page <= 100:
        raise ConfigError("hh.per_page должен быть целым числом от 1 до 100")

    check_roles(data.get("roles"))


def check_roles(roles):
    """Проверить, что у каждой роли есть id, title и поисковые запросы."""
    if not isinstance(roles, list) or not roles:
        raise ConfigError("раздел 'roles' должен быть непустым списком")

    seen_ids = set()

    for i, role in enumerate(roles):
        where = f"roles[{i}]"

        if not isinstance(role, dict):
            raise ConfigError(f"{where}: ожидался словарь")

        role_id = role.get("id")
        if not isinstance(role_id, str) or not role_id:
            raise ConfigError(f"{where}: не задан id")

        if role_id in seen_ids:
            raise ConfigError(f"{where}: повторяющийся id {role_id!r}")
        seen_ids.add(role_id)

        if not role.get("title"):
            raise ConfigError(f"{where}: не задан title")

        queries = role.get("queries")
        if not isinstance(queries, list) or not queries:
            raise ConfigError(f"{where}: queries должен быть непустым списком")

        for query in queries:
            if not isinstance(query, str) or not query.strip():
                raise ConfigError(f"{where}: поисковый запрос должен быть непустой строкой")
