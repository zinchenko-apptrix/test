# vt_starknetbridge

## Функционал

### deposit.py:
 - Создает кошелёк Argent X через selenium и сохраняет в таблицу StarknetAccountDeploy. (После этого selenium больше не юзается)
 - Берет адреса кошельков ETH из файла tsv, берет приватные ключи из
   таблицы выводов binance если они отсутствуют в файле.
 - Отправляет ETH в сеть StarkNet в созданный кошелек
 - Через 10 минут после каждого успешного перевода запускает деплой аккаунта StarkNet
 - Возможность использовать прокси сервера


### deploy.py:
 - Запускает деплой аккаунтов из таблицы StarknetAccountDeploy, у которых deployed = False и amount > 0.


## Подготовка к запуску
Требования: Python 3.8 (скачать тут https://www.python.org/downloads/) и Mozilla FireFox

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

## Запуск deposit.py

__Передаваемые аргументы:__

    --accounts-file - Путь до tsv файла c аккаунтами. Либо только адреса, либо адреса с ключами

    --proxies-file - Путь до текстового файла с прокси (необязательный параметр). Формат - host:port:user:pass 

    --min-amount-swap - Минимальная сумма свапа в % от баланса

    --max-amount-swap - Максимальная сумма свапа в % от баланса

    --max-gas-limit   - Максимальное количество газа за транзакцию бриджа, WEI

    --max-gas-price - максимальный GasPrice в сети Ethereum, WEI

    --max-fee-deploy - максимальная комиссия за деплой аккаунта в сети StarkNet (должна быть меньше чем баланс аккаунта), WEI

    --min-delay - минимальная задержка
   
    --max-delay - максимальная задержка

    
Пример запуска:
`python deposit.py --accounts-file accs.tsv --proxies-file proxies.txt --min-amount-swap 90 --max-amount-swap 100 --max-gas-limit 1000000000000 --max-gas-price 2000000000000 --max-fee-deploy 100000000000000 --min-delay 1 --max-delay 3`


## Запуск deploy.py

__Передаваемые аргументы:__

    --proxies-file - Путь до текстового файла с прокси (необязательный параметр). Формат - host:port:user:pass 

    --max-fee-deploy - максимальная комиссия за деплой аккаунта в сети StarkNet

    --min-delay - минимальная задержка
   
    --max-delay - максимальная задержка


    
Пример запуска:
`python deploy.py --max-fee-deploy 100000000000000 --min-delay 1 --max-delay 3`
