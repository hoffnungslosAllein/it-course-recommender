"""Командный интерфейс: python -m skillrec <команда>."""

import argparse
import sys

from . import __version__
from .config import ConfigError, load_config
from .db import DbError, init_db

# Команды пайплайна и их описания для справки.
STAGES = {
    "init-db": "создать базу данных и таблицы",
    "collect-stepik": "собрать курсы Stepik",
    "collect-hh": "собрать вакансии hh.ru",
    "build-profiles": "построить профили компетенций ролей",
    "recommend": "порекомендовать курсы для роли",
    "evaluate": "провести экспериментальную оценку",
}


def build_parser():
    """Собрать парсер аргументов со всеми командами."""
    parser = argparse.ArgumentParser(
        prog="python -m skillrec",
        description="Рекомендация образовательных курсов для ИТ-ролей.",
    )
    parser.add_argument("--version", action="version", version=f"skillrec {__version__}")
    parser.add_argument("--config", metavar="PATH", help="путь к config.yaml")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    for name, description in STAGES.items():
        sub = subparsers.add_parser(name, help=description, description=description)
        if name == "init-db":
            sub.add_argument(
                "--force",
                action="store_true",
                help="удалить существующую базу и создать заново",
            )

    return parser


def main(argv=None):
    """Разобрать аргументы и выполнить команду."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2

    if args.command == "init-db":
        return cmd_init_db(config, args)

    print(f"{args.command}: ещё не реализовано")
    return 1


def cmd_init_db(config, args):
    """Создать базу и вывести, что получилось."""
    try:
        result = init_db(config["paths"]["db"], force=args.force)
    except DbError as exc:
        print(f"Ошибка базы данных: {exc}", file=sys.stderr)
        return 2

    if result["fresh"]:
        status = "база создана заново"
    else:
        status = "схема применена к существующей базе"

    print(f"База данных: {result['path']}")
    print(f"Схема: версия {result['version']}")
    print(f"Таблиц: {len(result['tables'])}")
    print(f"Статус: {status}")
    return 0
