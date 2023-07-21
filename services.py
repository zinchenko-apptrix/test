import csv
import logging
import os
from random import choice

import requests
from selenium.webdriver.firefox.options import Options
from seleniumwire.webdriver import Firefox
from web3 import Web3

from database.other.models import ZkSyncProxyLog, BinanceWithdrawal

logger = logging.getLogger('starknet')


class FireFoxCreator:
    DRIVER_PATH = 'argent.xpi'

    def __init__(self, proxy=None):
        self.proxy = proxy
        self.driver = Firefox(
            options=self.get_options(),
            seleniumwire_options=self.get_seleniumwire_options()
        )
        self.add_params()

    def get_options(self):
        options = Options()
        options.add_argument('--headless')
        return options

    def get_seleniumwire_options(self):
        if self.proxy:
            return {'proxy': {'http': self.proxy}}

    def add_params(self):
        self.driver.install_addon(self.DRIVER_PATH, temporary=True)
        self.driver.implicitly_wait(15)


class AccountParser:
    """
    Парсинг приватных ключей из таблицы ZkSyncLiteBridge
    """
    def __init__(self, file_path: str, rpc):
        self.table = BinanceWithdrawal
        self.file_path = file_path
        self.private_keys = None
        self.w3 = Web3(Web3.HTTPProvider(endpoint_uri=rpc))
        self.addresses = self.get_addresses_from_file()

    def get_private_keys(self):
        """Get private keys from BinanceWithdrawal table"""
        if self.private_keys is not None:
            return self.private_keys
        accounts = self.table.get_by_addresses(self.addresses)
        if len(accounts) != len(self.addresses):
            withdrawal_addresses = [w.address for w in accounts]
            lost_addr = [a for a in self.addresses if a not in withdrawal_addresses]
            logger.error(f'Не найдены приватные ключи для {lost_addr}')
        return [(a.address, a.privateKey) for a in accounts if self.check_private_key(a)]

    def check_private_key(self, obj: BinanceWithdrawal):
        try:
            acc = self.w3.eth.account.from_key(obj.privateKey)
            if acc.address.lower() == obj.address.lower():
                return True
            logger.error(f'Неверный приватный ключ для {obj.address}')
        except Exception as e:
            logger.error(f'{e} {obj.address}')

    def get_addresses_from_file(self):
        self.validate_file()
        with open(self.file_path) as f:
            reader = csv.reader(f, delimiter='\t')
            lines = [a for a in reader]
        if len(lines[0]) > 1:
            self.private_keys = [
                (a[0], a[1]) for a in lines
                if self.check_private_key(
                    self.table(address=a[0], privateKey=a[1])
                )
            ]
        return [a[0] for a in lines]

    def validate_file(self):
        f = self.file_path
        if not os.path.isfile(f):
            raise ValueError(f'Файл не найден. {f}')
        if not f.endswith('.tsv') and not f.endswith('.csv'):
            raise ValueError(f'Формат файла должен быть tsv или csv {f}')


class ProxyAgent:
    def __init__(self, file):
        self.file = file
        self.proxies = self._parse_proxies_from_file()

    def _parse_proxies_from_file(self):
        if self.file:
            with open(self.file, 'r') as file:
                reader = csv.reader(file, delimiter=':')
                #  возвращается (логин, пароль, хост, порт)
                return [(p[2], p[3], p[0], p[1]) for p in reader]

    def rotate(self, address):
        proxy = self.get_proxy(address)
        if proxy:
            logger.info(f'{address} || proxy: {proxy}')
            return True
        else:
            self.reset_proxy()

    def get_proxy(self, address):
        used_proxy = ZkSyncProxyLog.get_proxy_str(address)
        if used_proxy and self.check_proxy(used_proxy):
            return used_proxy

        return self.get_proxy_from_file(address)

    def get_proxy_from_file(self, address):
        while self.proxies:
            proxy = choice(self.proxies)
            proxy_str = f'http://{proxy[0]}:{proxy[1]}@{proxy[2]}:{proxy[3]}'
            if self.check_proxy(proxy_str):
                ZkSyncProxyLog.create(
                    address=address,
                    username=proxy[0],
                    password=proxy[1],
                    host=proxy[2],
                    port=proxy[3],
                )
                return proxy_str
            else:
                self.proxies.remove(proxy)

    def check_proxy(self, proxy):
        os.environ['HTTPS_PROXY'] = proxy
        os.environ['HTTP_PROXY'] = proxy
        try:
            response = requests.get('https://google.com')
            if response.status_code == 200:
                return True
            ZkSyncProxyLog.kill_proxy(proxy)
        except BaseException as err:
            ZkSyncProxyLog.kill_proxy(proxy)
            logger.warning(f'Proxy error {proxy}: {err}')

    @staticmethod
    def reset_proxy():
        os.environ['HTTPS_PROXY'] = ''
        os.environ['HTTP_PROXY'] = ''
