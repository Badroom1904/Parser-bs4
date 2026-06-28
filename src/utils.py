import logging

from requests import RequestException
from exceptions import ParserFindTagException


def get_response(session, url):
    """Получение ответа от сервера с обработкой ошибок."""
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )
        return None


def find_tag(soup, tag, attrs=None):
    """Поиск тега с обработкой ошибок."""
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag
