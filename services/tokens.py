import json
import os

import requests
from web3 import Web3

from settings.config import PROJECT_DIR, MAIN_RPC

ABI_PATH = os.path.join(PROJECT_DIR, 'settings/contracts/abi')

TOKENS = {
    'USDC': {
        'address': '0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4',
        'decimals': 6,
        'abi': os.path.join(ABI_PATH, 'erc20.json')
    },
    'ETH': {
        'address': '0x0000000000000000000000000000000000000000',
        'decimals': 18,
        'abi': os.path.join(ABI_PATH, 'erc20.json')
    },
    'USDT': {
        'address': '0xf55BEC9cafDbE8730f096Aa55dad6D22d44099Df',
        'decimals': 6,
        'abi': os.path.join(ABI_PATH, 'erc20.json')
    },
}

WETH = '0x5300000000000000000000000000000000000004'


class CoinGecko:
    _instance = None
    TOKEN_MAP = {
        'ETH': 'ethereum',
        'DAI': 'dai',
        'USDC': 'usd-coin',
        'USDT': 'tether',
        'WBTC': 'bitcoin'
    }
    price_url = 'https://api.coingecko.com/api/v3/simple/price?vs_currencies={}&ids={}'

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.initialize(cls._instance)
        return cls._instance

    def initialize(self):
        tokens = 'dai,usd-coin,tether,bitcoin,ethereum'
        response = requests.get(url=self.price_url.format('usd', tokens)).json()
        self.rates = {
            'ETH': float(response['ethereum']['usd']),
            'USDC': float(response['usd-coin']['usd']),
            'DAI': float(response['dai']['usd']),
            'USDT': float(response['tether']['usd']),
            'WBTC': float(response['bitcoin']['usd']),
        }


class Token:
    def __init__(
        self,
        name: str,
        address: str,
        decimals: int,
        rpc: str,
        abi_file: str = None
    ):
        self.name = name
        self.address = address
        self.abi_file = abi_file
        self.decimals = decimals
        self.w3 = Web3(Web3.HTTPProvider(rpc))
        if abi_file:
            with open(abi_file, 'r') as abi:
                self.contr = self.w3.eth.contract(address=address, abi=json.load(abi))

    def allowance(self, owner: str, spender: str):
        return self.contr.functions.allowance(owner, spender).call()

    def to_wei(self, amount: float) -> int:
        return int(amount * 10 ** self.decimals)

    def from_wei(self, amount: int) -> int:
        return amount / 10 ** self.decimals

    def balance(self, address: str) -> int:
        if self.erc20:
            return self.contr.functions.balanceOf(address).call()
        return self.w3.eth.get_balance(self.w3.to_checksum_address(address))

    def balance_usd(self, address):
        response = CoinGecko().rates[self.name]
        return self.from_wei(self.balance(address)) * response

    @property
    def erc20(self):
        return self.name != 'ETH'

    def __repr__(self):
        return self.name


class TokenCreator:
    @staticmethod
    def get(name: str, rpc: str = MAIN_RPC):
        token_params = {
            'name': name,
            'address': TOKENS[name]['address'],
            'decimals': TOKENS[name]['decimals'],
            'rpc': rpc,
        }
        if name != 'ETH':
            token_params.update({'abi_file': TOKENS[name]['abi']})
        return Token(**token_params)
