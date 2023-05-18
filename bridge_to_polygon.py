import argparse
import logging
from logging.handlers import RotatingFileHandler

from aptos_sdk.account import Account
from aptos_sdk.client import RestClient
from eth_abi.packed import encode_packed
from database.models import PolygonAptosBridge, AptosPolygonBridge

NODE_URL = 'https://fullnode.mainnet.aptoslabs.com/v1'
EXPLORER = 'https://explorer.aptoslabs.com/txn/'
USDC_RESOURCE = '0x1::coin::CoinStore<0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC>'
USDC_MODULE = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
APT_RESOURCE = '0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>'
BRIDGE_FUNCTION = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::coin_bridge::send_coin_from"
MIN_NATIVE_FEE = 4000000

logger = logging.getLogger('stgstacking')
file_handler = RotatingFileHandler(
    filename='logs_from_aptos_to_polygon.log',
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


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с приватными ключами',
        default='accounts.tsv'
    )
    parser.add_argument(
        '--transfer-percent',
        help='Сколько баланса USDC переводим, %',
        type=int,
        default=100,
    )
    parser.add_argument(
        '--max-fee',
        help='Максимальный fee перевода, APT',
        type=int,
        default=4000000,
    )
    args = parser.parse_args()
    return (
        args.accounts_file,
        args.transfer_percent,
        args.max_fee,
    )


def get_adapter_params():
    """Второй аргумент это fee второй стороны моста (MATIC)"""
    adapter_param3 = encode_packed(["uint16", "uint64"], [1, 150000])
    return '0x' + adapter_param3.hex()


def get_usdc_balance(address):
    balance = client.account_resource(address, USDC_RESOURCE)['data']['coin']['value']
    if int(balance) == 0:
        raise ValueError(f'{address} | на счету нет USDC')
    return balance


def check_apt_balance(db_obj, max_fee):
    apt = client.account_resource(db_obj.addressAptos, APT_RESOURCE)['data']['coin']['value']
    if int(apt) < max_fee:
        raise ValueError(f'Недостаточно APT. {apt} < {max_fee}')


def get_fee_steps(max_fee: int):
    if max_fee < MIN_NATIVE_FEE:
        raise ValueError(f'Максимальное значение fee должно быть не меньше {MIN_NATIVE_FEE}')
    if max_fee == MIN_NATIVE_FEE:
        return [MIN_NATIVE_FEE]
    return [
        MIN_NATIVE_FEE,
        int((MIN_NATIVE_FEE + max_fee) / 2),
        max_fee
    ]


def create_transact(pa_bridge, amount, native_fee, sender_account):
    payload = {
        "type": "entry_function_payload",
        "arguments": [
            "109",
            pa_bridge.addressPolygon.replace('0x', '0x000000000000000000000000').lower(),
            str(amount),
            str(native_fee),  # 5519591  3207835 0.03207835
            '0',
            False,
            get_adapter_params(),
            '',
        ],
        "function": BRIDGE_FUNCTION,
        "type_arguments": [USDC_MODULE]
    }
    txn = client.submit_transaction(sender=sender_account, payload=payload)
    client.wait_for_transaction(txn)
    AptosPolygonBridge.create(
        addressAptos=pa_bridge.addressAptos,
        privateKeyAptos=pa_bridge.privateKeyAptos,
        addressPolygon=pa_bridge.addressPolygon,
        privateKeyPolygon=pa_bridge.privateKeyPolygon,
        aptos_txn=txn,
        amount=amount / 10**6,
    )
    logger.info(f'{pa_bridge.addressAptos} | SUCCESS txn: {EXPLORER}{txn}')


def bridge(address, percent, fee_steps):
    for fee in fee_steps:
        pa_bridge = PolygonAptosBridge.get_by_polygon_address(address=address, claimed=True)
        if not pa_bridge:
            logger.error(f'{address} | Не найден в PolygonAptosBridge. Либо у аккаунта claimed=False')
            return
        check_apt_balance(pa_bridge, fee)
        sender_account = Account.load_key(pa_bridge.privateKeyAptos)
        balance_usdc = get_usdc_balance(pa_bridge.addressAptos)
        amount = int(int(balance_usdc) * percent / 100)
        logger.info(f'{pa_bridge.addressAptos} | amount: {amount / 10**6} USDC, fee: {fee / 10**8} APT')
        try:
            create_transact(pa_bridge, amount, fee, sender_account)
            return
        except AssertionError as error:
            if "ELAYERZERO_INSUFFICIENT_FEE(0x10000)" not in error.args[0]:
                logger.error(f'{pa_bridge.addressAptos} | {error}')
                return
            logger.info(f'{pa_bridge.addressAptos} | слишком низкое FEE, повышаю')
    else:
        logger.error(f'{pa_bridge.addressAptos} | FEE достигла предела')


if __name__ == '__main__':
    file, percent, max_fee = parse_args()
    network = 'MATIC'
    fee_steps = get_fee_steps(max_fee)
    client = RestClient(NODE_URL)
    client.client_config.max_gas_amount = 250
    with open(file, "r") as f:
        addresses = [row.strip() for row in f]

    for address in addresses:
        try:
            bridge(address, percent, fee_steps)
        except BaseException as error:
            logger.error(f'{address} | {error}')
