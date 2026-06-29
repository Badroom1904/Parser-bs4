# Парсер документации Python и PEP

Парсер для сбора информации о документации Python и статусах PEP (Python Enhancement Proposals).

## 📋 О проекте

Проект представляет собой набор парсеров для сайта документации Python. Включает четыре режима работы:

- **whats-new** — сбор информации о новых возможностях в версиях Python
- **latest-versions** — получение списка версий документации Python
- **download** — скачивание архива с документацией
- **pep** — парсинг статусов всех PEP с проверкой соответствия

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/badroom1904/Parser-bs4.git
cd bs4_parser_pep-main

2. Создание и активация виртуального окружения

python -m venv venv
venv\Scripts\activate

macOS/Linux:

python3 -m venv venv
source venv/bin/activate

3. Установка зависимостей

pip install -r requirements.txt

4. Использование

# Парсинг новых возможностей Python
python src/main.py whats-new

# Парсинг версий документации
python src/main.py latest-versions

# Скачивание архива документации
python src/main.py download

# Парсинг статусов PEP (основной режим)
python src/main.py pep

4.1 Дополнительные опции

# Вывод в виде красивой таблицы
python src/main.py pep -o pretty

# Сохранение результата в CSV-файл
python src/main.py pep -o file

# Очистка кеша перед запуском
python src/main.py pep -c

# Комбинирование опций
python src/main.py pep -c -o file