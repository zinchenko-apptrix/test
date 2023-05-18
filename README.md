# vt_aptosbridge

## Функционал

- bridge_to_aptos.py - перевод USDC из polygon в aptos
- claim_usdc.py - подтверждение получения USDC на стороне aptos. Нужно выполнять не раньше, чем через 25 минут после моста, т.к. транзакция долго подтверждается (20м минимум)
- bridge_to_polygon.py - перевод USDC из aptos в polygon. Транзакция подтверждается 2-3 дня


## Подготовка к запуску
Требования: Python 3.8 (скачать тут https://www.python.org/downloads/)

Установка виртуального окружения и клонирование репозитория:

`pip install virtualenv`

`virtualenv --python="C:\Users\{USERNAME}\AppData\Local\Programs\Python\Python38\python.exe" dir_name`

`cd dir_name`

`Scripts\activate`

`git clone {repository_uri} src` (или через GitHub Desktop)

`cd src`

Установка зависимостей:

`pip install -r requirements.txt`


__Необходимо создать .env файл со следующими ключами:__

    POSTGRES_USER=
    POSTGRES_PASSWORD=
    POSTGRES_HOST=
    POSTGRES_PORT=
    POSTGRES_DB=
    SSL_CERT=путь до файла с расширением crt
    SSL_KEY=путь до файла с расширением key

Применить миграции:

`alembic upgrade head`

## Запуск bridge_to_aptos.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv/csv файла содержащего один столбец с КЛЮЧАМИ

    --transfer-percent - сколько переводить USDC, %

    --max-fee - максимальная комиссия за перевод, wei. из нее так же берется сумма для пополнения APT на стороне APTOS (что бы там было 5800000 - 6200000 wei APT, это 0.058-0.062 APT).
    Обычно это значение 1100000000000000000 - 1200000000000000000, или 1.1-1.2 MATIC

    --claim - Если передать в это значение 1, то через 30 минут после окончания переводов запустится claim скрипт для переданных аккаунтов


Пример запуска:

`python bridge_to_aptos.py --accounts-file accounts.tsv --transfer-percent 100 --max-fee 1300000000000000000`


## Запуск claim_usdc.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv/csv файла содержащего один столбец с КЛЮЧАМИ

Пример запуска:
`python claim_usdc.py --accounts-file accounts.tsv`


## Запуск bridge_to_polygon.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv/csv файла содержащего один столбец с КЛЮЧАМИ

    --transfer-percent - сколько переводить USDC, %

    --max-fee - максимальная комиссия за перевод, wei. Минимальное значение 4000000, оно же стоит по дефолту если не 
    передавать этот параметр


Пример запуска:

`python bridge_to_polygon.py --accounts-file accounts.tsv --transfer-percent 100`
