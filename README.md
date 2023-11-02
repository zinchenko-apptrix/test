# scroll_combine

## Функционал

### combine.py:
 - Создание транзакций с применением выбранных протоколов и токенов.
 - Берет адреса из файла tsv, берет приватные ключи из таблицы Accounts
 - Создаёт запись в таблице ScrollCombine
 - Используются прокси сервера из таблицы Proxy


### binance_rhino.py
 - Вывод ETH из бинанса в арбитрум, после получения средств - мост через https://app.rhino.fi/ в сеть Scroll
 - Берет адреса из файла tsv, берет приватные ключи из таблицы Accounts
 - Создаёт запись в таблице BinanceWithdrawals и RhinoBridge
 - Используются прокси сервера из таблицы Proxy


##### Таблица доступных протоколов и токенов

|            | ETH | USDC | USDT |
|------------|:---:|:----:|:----:|
| PunkSwap   |  +  |  +   |  +   |
| ScrollSwap |  +  |      |  +   |


## Подготовка к запуску
Требования: Python 3.11 (скачать тут https://www.python.org/downloads/)

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
    ETH_RPC=RPC сети ETHEREUM
    MAIN_RPC=RPC сети SCROLL
    ARBITRUM_RPC=RPC сети ARBITRUM
    PROJECT=
    BINANCE_API_KEY=
    BINANCE_SECRET=

Применить миграции:

`alembic upgrade head`

## Запуск combine.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv файла c аккаунтами

    --min-balance - Минимальный баланс переводимого токена на кошельке в $
    
    --min-remains - Минимум сколько должно остаться эфира на балансе после свапа эфира, ETH 

    --tokens - Токены для свапа через запятую. Доступные токены указаны в таблице

    --protocols - Протоколы для свапа через запятую. Доступные протоколы указаны в таблице

    --unique - Если передать 1 в этот параметр, то протоколы будут одноразовыми для каждого аккаунта
    
    --toeth - Если передать 1, то на каждом акке выполнятся только по 1 транзе на каждый переданный стейбл в ETH, используя переданные протоколы

    --min-count-txn - Минимальное количество транзакций на аккаунт

    --max-count-txn - Максимальное количество транзакций на аккаунт

    --min-amount-eth - Минимальная сумма в % от баланса для пар с ETH

    --max-amount-eth - Максимальная сумма в % от баланса для пар с ETH
   
    --min-amount-stables - Минимальная сумма свапа в % от баланса для пар без ETH

    --max-amount-stables - Максимальная сумма свапа в % от баланса для пар без ETH
    
    --small-transactions-percent - Какой % маленьких транзакций сделать среди больших. Пример: дано 6 больших, передан параметр 50, значит будет добавлено 3 маленьких транзакции.

    --small-protocols - Участвующие в маленьких транзакциях протоколы, через запятую

    --small-tokens - Участвующие в маленьких транзакциях токены, через запятую
    
    --small-amount-percent - Какой % объема используем в маленьких транзакциях
   
    --small-min-balance - Минимальный баланс переводимого токена на кошельке в $ для маленьких транзакций
   
    --small-transactions-slippage-eth - Slippage обмена в % для маленьких транзакций в парах с ETH

    --small-transactions-slippage-stable - Slippage обмена в % для маленьких транзакций в парах c двумя стейблами

    --max-gas-price - максимальный GasPrice в сети SCROLL в WEI

    --max-gas-price-l1 - максимальный GasPrice в сети ETHEREUM в WEI

    --max-gas-limit - максимальное количество газа на транзакцию, WEI
    
    --slippage-eth - Slippage обмена в % для основных транзакций в парах с ETH

    --slippage-stable - Slippage обмена в % для основных транзакций в парах c двумя стейблами

    --retries - Количество повторных попыток обмена после получения ошибки
    
    --retry-delay - Количество секунд между повторными попытками

    --min-delay - минимальная задержка между свапами
   
    --max-delay - максимальная задержка между свапами
    
Пример запуска:
`python combine.py --accounts-file accs.tsv --min-balance 50 --min-remains 0.001 --tokens ETH,USDC,USDT --protocols SyncSwap,KyberSwap --min-count-txn 1 --max-count-txn 3 --min-amount-stables 90 --max-amount-stables 100 --min-amount-eth 40 --max-amount-eth 50 --max-gas-price 250000000000 --slippage-eth 1 --slippage-stable 2 --retries 10 --retry-delay 50 --min-delay 1 --max-delay 3`


## Запуск combine.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv файла c аккаунтами 1. Адрес Arbitrum 2. min_ETH 3. max_ETH 4. max_binance_fee_withdrawal
    
    --full-balance-bridge - если передан параметр (1), то в бридже будет использоваться 
    весь баланс арбитрума. Если не передан параметр, то в бридже используется то 
    количество ETH, которое было выведено из бинанса
    
    --decimals - количество знаков после точки в сумме вывода из бинанса
    
    --max-gas-price-l2 - Стоимость газа в сети Arbitrum, WEI

    --max-gas-price-l1 - Стоимость газа в сети ETHEREUM, WEI

    --min-delay - минимальная задержка между свапами
   
    --max-delay - максимальная задержка между свапами
    
Пример запуска:
`python combine.py --accounts-file accs.tsv --max-gas-price-l1 500000000000 --max-gas-price-l2 500000000000 --min-delay 1 --max-delay 3`
