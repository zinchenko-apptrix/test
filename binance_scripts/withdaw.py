import random
from time import sleep

from binance.spot import Spot

from services.logger import logger
from settings.config import BINANCE_SECRET, BINANCE_API_KEY


class WithdrawalBinance:
    """Вывод средств из биржи Binance на новые кошельки"""

    def __init__(
        self,
        client: Spot,
        address: str,
        network: str,
        ccy: str,
        max_withdraw_fee: float,
    ):
        self.client = client
        self.address = address
        self.network = network
        self.ccy = ccy
        self.max_withdraw_fee = max_withdraw_fee

    def withdraw(self, amount):
        self.check_min_transfer(amount)
        self.check_withdraw_fee()
        return self._withdraw(amount)

    def _withdraw(self, amount):
        """Submit request of withdrawal"""
        logger.info(
            f'Переводим {amount} {self.ccy} на {self.address} '
            f'в сети {self.network}'
        )
        resp = self.client.withdraw(
            coin=self.ccy,
            amount=amount,
            address=self.address,
            network=self.network,
        )
        withdrawal_id = resp['id']
        logger.info(f'Перевели {amount} {self.ccy} на {self.address}')
        return withdrawal_id

    def check_min_transfer(self, amount: float):
        """Check minWithdrawal for coin and network"""
        network = self.get_network()
        withdraw_min = float(network['withdrawMin'])
        if amount < withdraw_min:
            logger.error(
                f'Минимальная сумма перевода: {withdraw_min}. '
                f'{amount} < {withdraw_min}'
            )
            raise ValueError('Слишком низкий нижний порог перевода')

    def get_network(self):
        all_coins = self.client.coin_info()
        my_coin = [c for c in all_coins if c['coin'] == self.ccy][0]
        networks = my_coin['networkList']
        my_network = [n for n in networks if n['network'] == self.network]
        if not my_network:
            raise ValueError(f'Некорректное значение network: {self.network}')
        return my_network[0]

    def check_withdraw_fee(self):
        """Проверяем комиссию вывода. Если она высокая - ждём снижения"""
        while 1:
            network = self.get_network()
            fee = float(network['withdrawFee'])
            if fee <= self.max_withdraw_fee:
                break
            logger.info(f'Withdraw fee выше желаемого: {fee}. Ждем 60 сек')
            sleep(60)


def withdraw_binance(
    address: str,
    network: str,
    ccy: str,
    max_withdraw_fee: float,
    amount: float,
):
    client = Spot(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET)
    router = WithdrawalBinance(client, address, network, ccy, max_withdraw_fee)
    return router.withdraw(amount)
