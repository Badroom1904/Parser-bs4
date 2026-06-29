import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL, EXPECTED_STATUS
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    """Парсинг страницы What's New."""
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'})

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue

        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ') if dl else ''
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    """Парсинг страницы с версиями Python."""
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')

    for ul in ul_tags:
        if 'Python' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Не найден список c версиями Python')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'

    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append((link, version, status))

    return results


def download(session):
    """Скачивание архива с документацией."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = soup.find('div', {'role': 'main'})
    if main_tag is None:
        logging.error('Не найден main_tag')
        return

    table_tag = main_tag.find('table', {'class': 'docutils'})
    if table_tag is None:
        logging.error('Не найден table_tag')
        return

    pdf_a4_tag = table_tag.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    if pdf_a4_tag is None:
        pdf_a4_tag = table_tag.find('a', {'href': re.compile(r'.*\.zip$')})
        if pdf_a4_tag is None:
            logging.error('Не найден pdf_a4_tag')
            downloads_dir = BASE_DIR / 'downloads'
            downloads_dir.mkdir(exist_ok=True)
            logging.info('Папка downloads создана (архив не найден)')
            return

    archive_url = urljoin(downloads_url, pdf_a4_tag['href'])
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)

    filename = archive_url.split('/')[-1]
    archive_path = downloads_dir / filename

    logging.info(f'Начинается загрузка: {filename}')
    response = session.get(archive_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(archive_path, 'wb') as file:
        with tqdm(
            total=total_size, unit='B', unit_scale=True, desc=filename
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                pbar.update(len(chunk))

    logging.info(f'Архив успешно сохранён: {archive_path}')
    print(f'✓ Архив успешно сохранён: {archive_path}')


def get_pep_status(pep_soup, pep_url):
    """Извлекает статус PEP из страницы."""
    status_dt = None
    for dt in pep_soup.find_all('dt'):
        if 'Status' in dt.get_text():
            status_dt = dt
            break

    if status_dt is None:
        logging.warning(f'Не найден тег dt с Status на странице {pep_url}')
        return None

    status_dd = status_dt.find_next_sibling('dd')
    if status_dd is None:
        logging.warning(f'Не найден тег dd со статусом на странице {pep_url}')
        return None

    abbr_tag = status_dd.find('abbr')
    if abbr_tag:
        return abbr_tag.text.strip()
    return status_dd.text.strip()


def process_pep_row(row, session):
    """Обрабатывает одну строку таблицы PEP."""
    columns = row.find_all('td')
    if len(columns) < 3:
        return None, None, None

    pep_link_tag = columns[1].find('a')
    if not pep_link_tag:
        return None, None, None

    pep_url = urljoin(PEP_URL, pep_link_tag['href'])

    status_text = columns[0].text.strip()
    status_key = status_text[1:] if len(status_text) > 1 else ''
    expected_statuses = EXPECTED_STATUS.get(status_key, ())

    pep_response = get_response(session, pep_url)
    if pep_response is None:
        return None, None, None

    pep_soup = BeautifulSoup(pep_response.text, 'lxml')
    actual_status = get_pep_status(pep_soup, pep_url)

    if actual_status is None:
        return None, None, None

    return actual_status, expected_statuses, pep_url


def parse_pep_page(session, url):
    """Парсит одну страницу со списком PEP."""
    response = get_response(session, url)
    if response is None:
        return [], None

    soup = BeautifulSoup(response.text, features='lxml')

    # Находим ВСЕ таблицы с классом pep-zero-table
    tables = soup.find_all('table', attrs={'class': 'pep-zero-table'})
    if not tables:
        logging.error(f'Таблицы с PEP не найдены на странице {url}')
        return [], None

    all_rows = []
    for table in tables:
        rows = table.find_all('tr')
        if rows:
            # Пропускаем заголовок в каждой таблице
            all_rows.extend(rows[1:])

    if not all_rows:
        return [], None

    # Ищем ссылку на следующую страницу
    next_page = None
    nav = soup.find('nav', attrs={'aria-label': 'Page navigation'})
    if nav:
        next_link = nav.find('a', attrs={'rel': 'next'})
        if next_link:
            next_page = urljoin(url, next_link.get('href'))

    return all_rows, next_page


def pep(session):
    """Парсинг страниц PEP с пагинацией."""
    status_count = {}
    mismatched_peps = []
    current_url = PEP_URL
    page_number = 1

    while current_url:
        logging.info(f'Загрузка страницы {page_number}: {current_url}')
        rows, next_url = parse_pep_page(session, current_url)

        if not rows:
            logging.warning(f'На странице {current_url} нет данных')
            break

        for row in tqdm(rows, desc=f'Обработка PEP (страница {page_number})'):
            result = process_pep_row(row, session)
            actual_status, expected_statuses, pep_url = result
            if actual_status is None:
                continue

            if expected_statuses and actual_status not in expected_statuses:
                mismatched_peps.append((
                    pep_url, actual_status, expected_statuses))

            status_count[
                actual_status] = status_count.get(actual_status, 0) + 1

        current_url = next_url
        page_number += 1

    if mismatched_peps:
        logging.info('Несовпадающие статусы:')
        for url, actual, expected in mismatched_peps:
            logging.info(f'{url}')
            logging.info(f'Статус в карточке: {actual}')
            logging.info(f'Ожидаемые статусы: {list(expected)}')

    results = [('Статус', 'Количество')]
    results.extend((
        status, str(count)) for status, count in sorted(status_count.items()))

    total_count = sum(status_count.values())
    results.append(('Total', str(total_count)))

    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    """Основная функция парсера."""
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()

    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
