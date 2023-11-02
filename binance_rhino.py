import argparse
import csv
import traceback
from dataclasses import dataclass
from random import uniform, randint
from time import sleep

from binance_scripts.withdaw import withdraw_binance
from database.other.models import Account as AccountDB, BinanceWithdrawal, ProxySettings
from web3 import Web3

from protocols.rhino.rhino import bridge
from services.logger import logger
from services.proxy import ProxyAgent
from services.utils import eth_to_wei
from settings.config import ARBITRUM_RPC, GAS_WAITING


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с адресами кошельков',
        default='acc2.tsv'
    )
    parser.add_argument(
        '--full-balance-bridge',
        help='Бриджить всё что есть на аккаунте арбитрума в скролл',
        type=bool,
        default=False,
    )
    parser.add_argument(
        '--decimals',
        help='Количество знаков после точки при расчете amount',
        type=int,
        default=5
    )
    parser.add_argument(
        '--max-gas-price-l2',
        help='Максимальная стоимость газа в ARBITRUM',
        type=int,
        default=100000000000000,
    )
    parser.add_argument(
        '--max-gas-price-l1',
        help='Максимальная стоимость газа в ETHEREUM',
        type=int,
        default=10000000000000000,
    )
    parser.add_argument(
        '--min-delay',
        help='Минимальное время между выводами, с',
        type=int,
        default=1
    )
    parser.add_argument(
        '--max-delay',
        help='Максимальное время между выводами, с',
        type=int,
        default=5
    )
    args = parser.parse_args()
    return (
        args.accounts_file,
        args.full_balance_bridge,
        args.decimals,
        args.max_gas_price_l2,
        args.max_gas_price_l1,
        args.min_delay,
        args.max_delay,
    )


@dataclass
class Wallet:
    address: str
    private_key: str
    amount: float
    max_fee: float


def get_wallets(file_path: str, decimals_amount: int):
    with open(file_path) as f:
        reader = csv.reader(f, delimiter='\t')
        lines = [a for a in reader]
    return [
        Wallet(
            address=a[0],
            private_key=AccountDB.get_private_key(a[0]),
            amount=round(uniform(float(a[1]), float(a[2])), decimals_amount),
            max_fee=float(a[3]),
        ) for a in lines
    ]


def wait_balance(w3: Web3, address: str, old_balance: int):
    while 1:
        new_balance = w3.eth.get_balance(Web3.to_checksum_address(address))
        if new_balance > old_balance:
            logger.info(f'{address} || Balance increased')
            return new_balance
        logger.info(f'{address} || Pending replenishment')
        sleep(GAS_WAITING)


def main(
    wallet: Wallet,
    full_bridge: bool,
    max_gas_price_l2: int,
    max_gas_price_l1: int,
    proxy_address: str,
):
    ProxyAgent.reset_proxy()
    w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
    network, currency = 'ARBITRUM', 'ETH'
    cur_balance = w3.eth.get_balance(Web3.to_checksum_address(wallet.address))
    withdraw_id = withdraw_binance(
        address=wallet.address,
        network=network,
        ccy=currency,
        max_withdraw_fee=wallet.max_fee,
        amount=wallet.amount,
    )
    BinanceWithdrawal.create(
        binance_id=withdraw_id,
        address=wallet.address,
        network=network,
        currency=currency,
        amount=wallet.amount
    )
    cur_balance = wait_balance(w3, wallet.address, cur_balance)
    if cur_balance - eth_to_wei(wallet.amount) <= eth_to_wei(0.0004):
        full_bridge = True
    params = {
        'wallet': wallet,
        'max_gas_price_l2': max_gas_price_l2,
        'max_gas_price_l1': max_gas_price_l1,
        'proxy_address': proxy_address
    }
    if full_bridge:
        bridge(**params, max_balance=True)
    else:
        bridge(**params, amount=wallet.amount)


if __name__ == '__main__':
    (
        accounts_file,
        full_balance_bridge,
        decimals,
        max_gas_price_l2,
        max_gas_price_l1,
        min_delay,
        max_delay,
    ) = parse_args()
    proxy_settings = ProxySettings.get_last()
    proxy_agent = ProxyAgent(proxy_settings.retries, proxy_settings.retry_delay)
    wallets = get_wallets(accounts_file, decimals)
    for w in wallets:
        try:
            proxy = proxy_agent.get_proxy(w.address)
            if not proxy:
                continue
            main(
                w,
                full_balance_bridge,
                max_gas_price_l2,
                max_gas_price_l1,
                proxy.address
            )
            if w != wallets[-1]:
                sleep(randint(min_delay, max_delay))
        except BaseException as err:
            logger.error(traceback.format_exc())
            logger.error(f'{w.address} || Error: {err}')
    if proxy_agent.failed_customers:
        logger.warning(
            f'Accounts without proxies: '
            f'({len(proxy_agent.failed_customers)}): {proxy_agent.list_fails}'
        )
