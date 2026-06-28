import argparse
from outputs import configure_logging as _configure_logging


def configure_logging():
    """Настройка логирования (перенаправление в outputs)."""
    _configure_logging()


def configure_argument_parser(available_modes):
    """Настройка аргументов командной строки."""
    parser = argparse.ArgumentParser(description='Парсер документации Python')
    parser.add_argument(
        'mode',
        choices=available_modes,
        help='Режимы работы парсера'
    )
    parser.add_argument(
        '-c',
        '--clear-cache',
        action='store_true',
        help='Очистка кеша'
    )
    parser.add_argument(
        '-o',
        '--output',
        choices=('pretty', 'file'),
        help='Дополнительные способы вывода данных'
    )
    return parser
