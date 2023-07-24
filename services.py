import csv
import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from random import choice

import requests
from selenium.webdriver.firefox.options import Options
from seleniumwire.webdriver import Firefox
from web3 import Web3
from starknet_py.net.models import StarknetChainId
from starknet_py.net.networks import (
    TESTNET as TESTNET_CLIENT,
    MAINNET as MAINNET_CLIENT,
)
from database.other.models import ZkSyncProxyLog, BinanceWithdrawal

logger = logging.getLogger('starknet')


CLASS_HASH_PROXY = 0x025ec026985a3bf9d0cc1fe17326b245dfdc3ff89b8fde106542a3ea56c5a918
CLASS_HASH_ACCOUNT = 0x033434ad846cdd5f23eb73ff09fe6fddd568284a0fb7d1be20ee482f044dabe2
IMPLEMENT_FUNC = 215307247182100370520050591091822763712463273430149262739280891880522753123
TESTNET = os.getenv('TESTNET', False)
CLIENT = TESTNET_CLIENT if TESTNET else MAINNET_CLIENT
CHAIN = StarknetChainId.TESTNET if TESTNET else StarknetChainId.MAINNET

logger = logging.getLogger('starknet')
file_handler = RotatingFileHandler(
    filename='starknet.log',
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=3,
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


class Wallet:

    def __init__(self, address, private_key, eth_min, eth_max, retries=5):
        self.address = address
        self.private_key = private_key
        self.eth_min = float(eth_min)
        self.eth_max = float(eth_max)
        self.retries = retries

    def reduce(self, wallets):
        self.retries -= 1
        if self.retries <= 0:
            wallets.remove(self)
        logger.warning(f'{self.address} || Retries left: {self.retries}')


class AccountParser:
    def __init__(self, file_path: str, rpc):
        self.table = BinanceWithdrawal
        self.file_path = file_path
        self.private_keys = None
        self.w3 = Web3(Web3.HTTPProvider(endpoint_uri=rpc))
        self.addresses = self.get_addresses_from_file()

    def get_addresses_from_file(self):
        self.validate_file()
        with open(self.file_path) as f:
            reader = csv.reader(f, delimiter='\t')
            lines = [a for a in reader]
        if len(lines[0]) > 1:
            accounts = [
                Wallet(a[0], a[1], a[2], a[3]) for a in lines
                if a[4] == 'Starknet'
            ]
            return accounts

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


def eth_to_wei(amount):
    return int(amount * 10**18)


def wei_to_eth(amount):
    return amount / 10**18
