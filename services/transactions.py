from dataclasses import dataclass
from time import sleep
from typing import Callable

from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract.contract import ContractFunctions

from services.logger import logger
from services.tokens import Token
from settings.config import (
    GAS_PRICE_UP_RATE,
    GAS_WAITING,
    GAS_UP_RATE,
    MAIN_RPC,
    ETH_RPC,
    MAIN_SCAN,
)
from settings.types import Wei


@dataclass
class SignedTransaction:
    txn_hash: str
    value: int
    fee: int


def _check_max_gas_price_l1(decorated_function: Callable) -> Callable:
    def wrapper(self, *args, **kwargs):
        if self.max_gas_price_l1:
            self._get_suitable_gas_price(self.max_gas_price_l1, self.w3_l1)
        return decorated_function(self, *args, **kwargs)
    return wrapper


class TransactAgent:
    def __init__(
        self,
        account: LocalAccount,
        max_gas_price: Wei,
        max_gas_limit: int,
        max_gas_price_l1: Wei = None,
    ):
        self.account = account
        self.max_gas_price = max_gas_price
        self.max_gas_limit = max_gas_limit
        self.max_gas_price_l1 = max_gas_price_l1

        self.w3 = Web3(Web3.HTTPProvider(MAIN_RPC))
        self.w3_l1 = Web3(Web3.HTTPProvider(ETH_RPC))

    @_check_max_gas_price_l1
    def transact(self, txn_function: ContractFunctions, value: Wei = None) -> SignedTransaction:
        txn_data = self._create_txn_data(txn_function, value)
        raw_transaction = txn_function.build_transaction(txn_data)
        return self._process_transaction(raw_transaction)

    @_check_max_gas_price_l1
    def transact_encoded_data(self, raw_transaction: dict) -> SignedTransaction:
        raw_transaction.update({
            'gasPrice': self._get_suitable_gas_price(self.max_gas_price, self.w3),
            'gas': self._get_suitable_gas_from_encoded_txn(raw_transaction),
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        })
        return self._process_transaction(raw_transaction)

    def _process_transaction(self, raw_transaction: dict) -> SignedTransaction:
        txh_hash, gas_used = self._sign_raw_transaction(raw_transaction)
        fee = gas_used * raw_transaction.get('gasPrice')
        return SignedTransaction(txh_hash, raw_transaction.get('value'), fee)

    def _create_txn_data(self, txn_function: ContractFunctions, value: int) -> dict:
        txn_data = {
            'from': self.account.address,
            'gasPrice': self._get_suitable_gas_price(self.max_gas_price, self.w3),
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
        }
        if value is not None:
            txn_data['value'] = value
        txn_data['gas'] = self._get_suitable_gas_from_contract_function(txn_function, txn_data)
        return txn_data

    def _sign_raw_transaction(self, tx: dict) -> tuple[str, int]:
        signed = self.account.sign_transaction(tx)
        txn_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(txn_hash)
        if receipt.status != 1:
            raise ValueError(f'Transaction Failed {MAIN_SCAN}{txn_hash.hex()}')
        return receipt.transactionHash.hex(), receipt.gasUsed

    @staticmethod
    def _get_suitable_gas_price(max_gas_price: Wei, w3: Web3) -> int:
        while True:
            eth_gas_price = int(w3.eth.gas_price * GAS_PRICE_UP_RATE)
            if eth_gas_price <= max_gas_price:
                return eth_gas_price
            logger.warning(
                f'Exceeded gas price {w3.manager.provider.endpoint_uri} '
                f'{eth_gas_price} wei. Waiting'
            )
            sleep(GAS_WAITING)

    def _get_suitable_gas_from_encoded_txn(self, txn: dict) -> int:
        return self._get_suitable_gas(self.w3.eth.estimate_gas, txn)

    def _get_suitable_gas_from_contract_function(
        self, txn: ContractFunctions, txn_data: dict
    ) -> int:
        return self._get_suitable_gas(txn.estimate_gas, txn_data)

    def _get_suitable_gas(self, estimator: Callable, txn_data: dict):
        while 1:
            gas = int(estimator(txn_data) * GAS_UP_RATE)
            if gas <= self.max_gas_limit:
                return gas
            logger.warning(
                f'Exceeded gas limit {gas}. Waiting'
            )
            sleep(GAS_WAITING)


def check_allowance(token: Token, account: LocalAccount, spender: str, value: Wei):
    if not token.erc20:
        return
    if token.allowance(account.address, spender) < value:
        value *= 10
        return token.contr.functions.approve(spender, value)
