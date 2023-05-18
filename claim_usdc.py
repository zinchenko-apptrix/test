import argparse
import logging
import time
from logging.handlers import RotatingFileHandler

from aptos_sdk.account import Account
from aptos_sdk.client import RestClient

from database.models import PolygonAptosBridge

MIN_APT = 500000
MAX_GAS = 1000
NODE_URL = 'https://fullnode.mainnet.aptoslabs.com/v1'
USDC_RESOURCE = '0x1::coin::CoinStore<0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC>'
APT_RESOURCE = '0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>'
PAYLOAD = {
    "type": "entry_function_payload",
    "arguments": [],
    "function": "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::coin_bridge::claim_coin",
    "type_arguments": [
    "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
    ]
}


def get_logger():
    logger = logging.getLogger('stgstacking')
    file_handler = RotatingFileHandler(
        filename='logs.log',
        maxBytes=1024 * 1024 * 5,  # 5 MB
        backupCount=10,
        encoding='UTF-8',
    )
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] - %(message)s', '%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    return logger


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с приватными ключами',
        default='accounts.tsv'
    )
    args = parser.parse_args()
    return args.accounts_file


def claim_usdc(db_obj: PolygonAptosBridge, logger):
    try:
        client = RestClient(NODE_URL)
        client.client_config.max_gas_amount = MAX_GAS
        apt_balance_data = client.account_resource(db_obj.addressAptos, APT_RESOURCE)
        if int(apt_balance_data['data']['coin']['value']) < MIN_APT:
            logger.error(f'{db_obj.addressAptos} | Недостаточно APT')
            return
        account = Account.load_key(db_obj.privateKeyAptos)
        txn = client.submit_transaction(
            sender=account,
            payload=PAYLOAD
        )
        client.wait_for_transaction(txn)
        time.sleep(5)
        usdc_balance_data = client.account_resource(db_obj.addressAptos, USDC_RESOURCE)
        usdc_balance = usdc_balance_data['data']['coin']['value']
        db_obj.claim()
        logger.info(f"{db_obj.addressAptos} | УСПЕШНО claim {usdc_balance} USDC  tx {txn}")
    except Exception as error:
        logger.info(f"{db_obj.addressAptos} | НЕ УСПЕШНО claim USDC | {error}")


if __name__ == '__main__':
    file = parse_args()
    logger = get_logger()
    with open(file, "r") as f:
        addresses = [row.strip() for row in f]

    for address in addresses:
        db_obj = PolygonAptosBridge.get_by_polygon_address(address=address, amount=True)
        if not db_obj:
            logger.error(f'{addresses} | не найден в таблице PolygonAptosBridge. Либо у аккаунта amount=0')
            continue
        claim_usdc(db_obj, logger)
