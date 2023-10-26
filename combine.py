import argparse
import traceback
from random import choice, randint
from time import sleep

from eth_account import Account

from services.proxy import ProxyAgent
from services.account import AccountParser, Wallet
from services.steps import StepGenerator
from services.logger import logger
from database.other.models import ProxySettings, Proxy
from services.utils import eth_to_wei


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с адресами кошельков',
        default='accs.tsv'
    )
    parser.add_argument(
        '--min-balance',
        help='Минимальный баланс, который должен быть на кошельке в $',
        type=float,
        default=0.05,
    )
    parser.add_argument(
        '--min-remains',
        help='Минимальный баланс эфира, который должен остаться после свапа эфира',
        type=float,
        default=0.0001
    )
    parser.add_argument(
        '--tokens',
        help='Участвующие токены, через запятую (USDC,USDT,ETH)',
        type=str,
        default='ETH,USDC',
    )
    parser.add_argument(
        '--protocols',
        help='Участвующие протоколы, через запятую (KyberSwap,SyncSwap)',
        type=str,
        default='PunkSwap',
    )
    parser.add_argument(
        '--unique',
        help='Использовать 1 протокол только 1 раз на кошелек',
        type=bool,
        default=False,
    )
    parser.add_argument(
        '--toeth',
        help='Перевести стейблы в эфир на каждом аккаунте',
        type=bool,
        default=False,
    )
    parser.add_argument(
        '--min-count-txn',
        help='Минимальное количество транзакций',
        default=1,
        type=int,
    )
    parser.add_argument(
        '--max-count-txn',
        help='Максимальное количество транзакций',
        default=1,
        type=int,
    )
    parser.add_argument(
        '--min-amount-eth',
        help='Минимальная сумма свапа в % для ETH',
        default=3,
        type=int,
    )
    parser.add_argument(
        '--max-amount-eth',
        help='Максимальная сумма свапа в % для ETH',
        default=3,
        type=int,
    )
    parser.add_argument(
        '--min-amount-stables',
        help='Минимальная сумма свапа в % для пар без ETH',
        default=50,
        type=int,
    )
    parser.add_argument(
        '--max-amount-stables',
        help='Максимальная сумма свапа в % ля пар без ETH',
        default=50,
        type=int,
    )
    parser.add_argument(
        '--small-transactions-percent',
        help='Какой % маленьких транзакций сделать среди больших',
        default=0,
        type=float,
    )
    parser.add_argument(
        '--small-protocols',
        help='Участвующие в маленьких транзакциях протоколы, через запятую',
        type=str,
        default='10kSwapPool',
    )
    parser.add_argument(
        '--small-tokens',
        help='Участвующие в маленьких транзакциях токены, через запятую',
        type=str,
        default='ETH,USDT,USDC',
    )
    parser.add_argument(
        '--small-amount-percent',
        help='Какой % объема меняем в маленьких транзакциях',
        default=8.9,
        type=float,
    )
    parser.add_argument(
        '--small-min-balance',
        help='Минимальный баланс, который должен быть на кошельке в $ для маленьких транзакций',
        type=float,
        default=1,
    )
    parser.add_argument(
        '--small-transactions-slippage-eth',
        help='Slippage обмена в % для маленьких транзакций в парах с ETH',
        default=1,
        type=float,
    )
    parser.add_argument(
        '--small-transactions-slippage-stable',
        help='Slippage обмена в % для маленьких транзакций в парах c двумя стейблами',
        default=1,
        type=float,
    )
    parser.add_argument(
        '--max-gas-price',
        help='Максимальная стоимость газа в сети LINEA wei',
        default=2000000000000,
        type=int,
    )
    parser.add_argument(
        '--max-gas-price-l1',
        help='Максимальная стоимость газа в сети ETHEREUM wei',
        default=2000000000000,
        type=int,
    )
    parser.add_argument(
        '--max-gas-limit',
        help='Максимальное количество газа на транзакцию',
        default=2000000000000,
        type=int,
    )
    parser.add_argument(
        '--slippage-eth',
        help='Slippage обмена в % для основных транзакций в парах с ETH',
        default=1,
        type=float,
    )
    parser.add_argument(
        '--slippage-stable',
        help='Slippage обмена в % для основных транзакций в парах c двумя стейблами',
        default=1,
        type=float,
    )
    parser.add_argument(
        '--retries',
        help='Количество повторных попыток обмена после получения ошибки',
        default=1,
        type=int,
    )
    parser.add_argument(
        '--retry-delay',
        help='Количество секунд между повторными попытками',
        default=1,
        type=int,
    )
    parser.add_argument(
        '--min-delay',
        help='Минимальная задержка между переводами, с',
        type=int,
        default=5,
    )
    parser.add_argument(
        '--max-delay',
        help='Максимальная задержка между переводами, с',
        type=int,
        default=5,
    )
    args = parser.parse_args()
    return (
        args.accounts_file,
        args.min_balance,
        args.min_remains,
        args.tokens,
        args.protocols,
        args.unique,
        args.toeth,
        args.min_count_txn,
        args.max_count_txn,
        args.min_amount_eth,
        args.max_amount_eth,
        args.min_amount_stables,
        args.max_amount_stables,
        args.small_transactions_percent,
        args.small_protocols,
        args.small_tokens,
        args.small_amount_percent,
        args.small_min_balance,
        args.small_transactions_slippage_eth,
        args.small_transactions_slippage_stable,
        args.max_gas_price,
        args.max_gas_price_l1,
        args.max_gas_limit,
        args.slippage_eth,
        args.slippage_stable,
        args.retries,
        args.retry_delay,
        args.min_delay,
        args.max_delay,
    )


def make_action(router, retries: int, retry_delay: int):
    for i in range(retries + 1):
        try:
            router.go()
            return True
        except BaseException as err:
            logger.error(err)
            if i < retries:
                logger.warning(f'{router.account.address} || Retrying')
                sleep(retry_delay)


def main(wallet: Wallet, proxy: Proxy, retries: int, retry_delay: int):
    step = choice(wallet.steps)
    account = Account.from_key(wallet.private_key)
    failed_protocols = []
    for _ in range(len(step.protocols)):
        not_checked_protocols = [p for p in step.protocols if p not in failed_protocols]
        if step.unique_protocols:
            not_checked_protocols = [
                p for p in not_checked_protocols if p not in wallet.used_protocols
            ]
        protocol_class = choice(not_checked_protocols)
        router = protocol_class(account=account, proxy=proxy, **step.__dict__)
        if router.ready():
            result_success = make_action(router, retries, retry_delay)
            if result_success:
                wallet.steps.remove(step)
                wallet.used_protocols.append(protocol_class)
            break
        else:
            failed_protocols.append(protocol_class)
    else:
        if step.toeth:
            wallet.steps = []
            return
        raise ValueError(f'Not found protocol to use')


if __name__ == '__main__':
    (
        accounts_file,
        min_balance,
        min_remains,
        tokens,
        protocols,
        unique,
        toeth,
        min_count_txn,
        max_count_txn,
        min_amount_eth,
        max_amount_eth,
        min_amount_stables,
        max_amount_stables,
        small_transactions_percent,
        small_protocols,
        small_tokens,
        small_amount_percent,
        small_min_balance,
        small_transactions_slippage_eth,
        small_transactions_slippage_stable,
        max_gas_price,
        max_gas_price_l1,
        max_gas_limit,
        slippage_eth,
        slippage_stable,
        retries,
        retry_delay,
        min_delay,
        max_delay,
    ) = parse_args()
    min_balance = max(min_balance, 0.01)
    min_remains = eth_to_wei(min_remains)
    wallets = AccountParser(accounts_file).get_wallets()
    proxy_settings = ProxySettings.get_last()
    proxy_agent = ProxyAgent(proxy_settings.retries, proxy_settings.retry_delay)
    StepGenerator(wallets).generate(
        min_balance_usd=min_balance,
        min_remains=min_remains,
        tokens=tokens.split(','),
        protocols=protocols.split(','),
        unique=unique,
        toeth=toeth,
        min_count_txn=min_count_txn,
        max_count_txn=max_count_txn,
        min_amount_eth=min_amount_eth,
        max_amount_eth=max_amount_eth,
        min_amount_stables=min_amount_stables,
        max_amount_stables=max_amount_stables,
        small_transactions_percent=small_transactions_percent,
        small_protocols=small_protocols.split(','),
        small_tokens=small_tokens.split(','),
        small_amount_percent=small_amount_percent,
        small_min_balance=small_min_balance,
        small_transactions_slippage_eth=small_transactions_slippage_eth,
        small_transactions_slippage_stable=small_transactions_slippage_stable,
        max_gas_price=max_gas_price,
        max_gas_price_l1=max_gas_price_l1,
        max_gas_limit=max_gas_limit,
        slippage_eth=slippage_eth,
        slippage_stable=slippage_stable,
    )

    while wallets:
        logger.info('- ' * 60)
        wallet = choice(wallets)
        proxy = proxy_agent.rotate(wallet.address)
        if not proxy:
            wallets.remove(wallet)
            continue
        try:
            main(wallet, proxy, retries, retry_delay)
            if not wallet.steps:
                wallets.remove(wallet)
            sleep(randint(min_delay, max_delay))
        except BaseException as error:
            wallets.remove(wallet)
            logger.error(traceback.format_exc())
            logger.error(f'{wallet.address} || Error: {error}')
    if proxy_agent.failed_customers:
        logger.warning(
            f'Аккаунты на которые не нашлось проксей '
            f'({len(proxy_agent.failed_customers)}): {proxy_agent.list_fails}'
        )
