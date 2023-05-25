# vt_traderjoe_bitcoinbridge

## Функционал

### buy_btc.py:
 - Обмен AVAX на BTCb в сети Avalanche через https://traderjoexyz.com/avalanche/trade 
 - Запись транзакций в таблицу BitcoinBridgeTraderJoeSwap
 - Кошельки берет из входящего файла, который может быть с ключами или без ключей.
Берет ключи из таблицы BinanceWithdrawals, если ключей в файле нет


### bitcoinbridge.py
 - Перенос BTCb из между AVALANCHE и POLYGON
 - Запись транзакций в таблицу BitcoinBridgeSwap
 - Кошельки берет из входящего файла, который может быть с ключами или без ключей.
Берет ключи из таблицы BitcoinBridgeTraderJoeSwap, если ключей в файле нет


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

`pip install git+https://github.com/zksync-sdk/zksync-python.git`

__Необходимо создать .env файл со следующими ключами:__

    POSTGRES_USER=
    POSTGRES_PASSWORD=
    POSTGRES_HOST=
    POSTGRES_PORT=
    POSTGRES_DB=
    SSL_CERT=путь до файла с расширением crt
    SSL_KEY=путь до файла с расширением key

    Необязательные параметры, у которых есть значения по умолчанию, если их не указать:
    AVALANCHE_RPC=https://api.avax.network/ext/bc/C/rpc
    POLYGON_RPC=https://polygon-mainnet.public.blastapi.io

Применить миграции:

`alembic upgrade head`

## Запуск buy_btc.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv файла c аккаунтами. Либо только адреса, либо адреса с ключами

    --min-amount - Минимальная сумма перевода AVAX

    --max-amount - Максимальная сумма перевода AVAX
    
    --max-gas-price - максимальный GasPrice, wei

    --min-delay - минимальная задержка
   
    --max-delay - максимальная задержка

    
Пример запуска:
`python buy_btc.py --accounts-file accounts.tsv --min-amount 0.0001 --max-amount 0.1 --max-gas-price 100000000000 --min-delay 1 --max-delay 2`


## Запуск bitcoinbridge.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv файла c аккаунтами. Либо только адреса, либо адреса с ключами
    
    --src - сеть источник (POLYGON или AVALANCHE)

    --min-amount-percent - Минимальная сумма перевода BTCb в %

    --max-amount-percent - Максимальная сумма перевода BTCb в %
    
    --max-gas-price - максимальный GasPrice, wei

    --max-fee - максимальная комиссия перевода, wei

    --min-delay - минимальная задержка
   
    --max-delay - максимальная задержка


Пример запуска:
`python bitcoinbridge.py --accounts-file accounts.tsv --src POLYGON --min-amount-percent 10 --max-amount-percent 25 --max-gas-price 10000000000000 --max-fee 1000000000000000000 --min-delay 1 --max-delay 2`

`python bitcoinbridge.py --accounts-file accounts.tsv --src AVALANCHE --min-amount-percent 10 --max-amount-percent 25 --max-gas-price 100000000000 --max-fee 100000000000000000 --min-delay 1 --max-delay 2`
