import json
from abc import abstractmethod
from dataclasses import dataclass
from random import shuffle, choice, randint
from time import sleep
from typing import Generic, TypeVar, Type, Sequence

from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract.contract import ContractFunctions
from web3.types import Wei

from database.models import ScrollCombine
from protocols.base import IProtocol, ContractMixin
from services.exchanger import GeckoExchanger
from services.logger import logger
from services.tokens import Token, TokenCreator, WETH
from services.transactions import TransactAgent, check_allowance, SignedTransaction
from services.utils import wei_to_eth
from settings.config import MAIN_RPC, MAIN_SCAN


@dataclass
class BaseTransaction:
    dst_amount: Wei
    value: Wei
    txn: ContractFunctions | dict


@dataclass
class SwapTransaction(BaseTransaction):
    txn: ContractFunctions


@dataclass
class AggregatorTransaction(BaseTransaction):
    txn: dict


ResponseTransaction = TypeVar('ResponseTransaction', bound=BaseTransaction)


class SwapBase(Generic[ResponseTransaction], ContractMixin):
    exchanger: Type[GeckoExchanger] = GeckoExchanger

    def __init__(
        self,
        account: LocalAccount,
        src_token: Token,
        dst_token: Token,
        slippage: float,
    ):
        self.account = account
        self.src_token = src_token
        self.dst_token = dst_token
        self.slippage = slippage

        if self.src_token.name == 'ETH':
            self.src_token.address = WETH
        if self.dst_token.name == 'ETH':
            self.dst_token.address = WETH

        self.w3 = Web3(Web3.HTTPProvider(MAIN_RPC))
        self.router = self._get_contract()

    def swap(self, amount: Wei) -> ResponseTransaction:
        txn, amount_dst_min = self._get_txn(amount)
        value = amount if not self.src_token.erc20 else None
        return SwapTransaction(txn=txn, dst_amount=amount_dst_min, value=value)

    def _get_min_dst(self, amount: Wei) -> Wei:
        dst_amount = self.dst_token.to_wei(self.exchanger.exchange(
            self.src_token, self.dst_token, self.src_token.from_wei(amount)
        ))
        dst_amount_with_slippage = Wei(int(dst_amount * (1 - self.slippage / 100)))
        if self.dst_token.decimals == 6:
            return dst_amount_with_slippage // 10 ** 4 * 10 ** 4
        return dst_amount_with_slippage


SwapClass = TypeVar('SwapClass', bound=SwapBase)


class SwapAgentBase(IProtocol, Generic[SwapClass]):
    TOKENS: Sequence[str]
    SWAP_CLASS: Type[SwapBase]

    def __init__(
        self,
        account,
        tokens: list[str],
        min_balance_usd: float,
        min_remains_eth_wei: int,
        amount_eth: float,
        amount_stable: float,
        slippage_eth: float,
        slippage_stable: float,
        max_gas_price: int,
        max_gas_price_l1: int,
        max_gas_limit: int,
        toeth: bool,
        size: str,
        *args,
        **kwargs,
    ):
        self.account = account
        self.tokens = [t for t in tokens if t in self.TOKENS]
        shuffle(self.tokens)
        self.min_balance_usd = min_balance_usd
        self.min_remains_eth_wei = min_remains_eth_wei
        self.amount_eth = amount_eth
        self.amount_stable = amount_stable
        self.slippage_eth = slippage_eth
        self.slippage_stable = slippage_stable
        self.max_gas_price = max_gas_price
        self.max_gas_price_l1 = max_gas_price_l1
        self.toeth = toeth
        self.size = size
        self._swapper: SwapClass | None = None
        self._txn_agent = TransactAgent(
            account=self.account,
            max_gas_limit=max_gas_limit,
            max_gas_price=self.max_gas_price,
            max_gas_price_l1=self.max_gas_price_l1,
        )

    def ready(self):
        if len(self.tokens) >= 2:
            tokens = self.tokens
            if self.toeth or self.amount_eth <= 0:
                tokens = [t for t in tokens if t != 'ETH']
            for t in tokens:
                token = TokenCreator.get(t)
                if (
                    token.balance_usd(self.account.address) >= self.min_balance_usd
                    and self._check(token)
                    and self._prepare_swap(token)
                ):
                    return True

    def _prepare_swap(self, src_token: Token):
        dst_tokens = self._get_dst_tokens(src_token)
        if not dst_tokens:
            return
        for _ in dst_tokens:
            dst_token = choice(dst_tokens)
            slippage, amount_percent = self._get_swap_params(src_token.name, dst_token)
            amount_swap = int(src_token.balance(self.account.address) / 100 * amount_percent)
            self._swapper = self.SWAP_CLASS(
                self.account,
                src_token=src_token,
                dst_token=TokenCreator.get(dst_token),
                slippage=slippage,
            )
            if amount_swap <= 0:
                return
            if src_token.name == 'ETH' and not self._check_min_remains(amount_swap):
                return
            if src_token.decimals >= 16:
                amount_swap = int(amount_swap / 10**10) * 10**10
            self._amount_swap = amount_swap
            logger.info(
                f'{self.account.address} || Protocol: {self.name}. {self.size}. '
                f'Slippage {slippage}%. Amount: {amount_percent}%. '
                f'{src_token.from_wei(self._amount_swap)} {src_token} > {dst_token}'
            )
            return True

    def go(self):
        swap_txn = self._swapper.swap(self._amount_swap)
        self._approve()
        success_txn = self._swap(swap_txn.txn, swap_txn.value)
        ScrollCombine.create(
            address=self.account.address,
            protocol=self.name,
            srcCurrency=self._swapper.src_token.name,
            dstCurrency=self._swapper.dst_token.name,
            srcAmount=self._swapper.src_token.from_wei(self._amount_swap),
            dstAmount=self._swapper.dst_token.from_wei(swap_txn.dst_amount),
            txnHash=success_txn.txn_hash,
            fee=wei_to_eth(success_txn.fee),
        )
        logger.info(f'{self.account.address} || Success swap. Fee: {wei_to_eth(success_txn.fee)} '
                    f'ETH - {MAIN_SCAN}{success_txn.txn_hash}. ')
        return True

    def _approve(self):
        approve_txn = check_allowance(
            self._swapper.src_token, self.account, self._swapper.CONTRACT, self._amount_swap)
        if approve_txn:
            logger.info(f'{self.account.address} || Approving '
                        f'{self._swapper.src_token.from_wei(approve_txn.args[1])} '
                        f'{self._swapper.src_token}')
            approve_txn = self._txn_agent.transact(approve_txn)
            logger.info(f'{self.account.address} || Success approving. Fee: '
                        f'{wei_to_eth(approve_txn.fee)} ETH')
            ScrollCombine.create(
                address=self.account.address,
                protocol='Approve',
                srcCurrency=self._swapper.src_token.name,
                txnHash=approve_txn.txn_hash,
                fee=wei_to_eth(approve_txn.fee),
                approvedFor=self.name,
            )
            sleep(randint(15, 25))

    @abstractmethod
    def _swap(self, *args, **kwargs) -> SignedTransaction:
        ...

    def _check(self, src_token: Token):
        return True

    def _update_dst_tokens(self, available_dst_tokens, src_token):
        return available_dst_tokens

    def _check_min_remains(self, amount_swap: int):
        balance = self._swapper.src_token.balance(self.account.address)
        post_swap_amount = balance - amount_swap
        if post_swap_amount >= self.min_remains_eth_wei:
            return True

    def _get_swap_params(self, src_token, dst_token):
        if 'ETH' in dst_token + src_token:
            slippage = self.slippage_eth
            amount_percent = self.amount_eth
        else:
            slippage = self.slippage_stable
            amount_percent = self.amount_stable
        return slippage, amount_percent

    def _get_dst_tokens(self, src_token: Token):
        available_dst_tokens = [t for t in self.tokens if t != src_token.name]
        if self.toeth:
            available_dst_tokens = ['ETH']
        if self.amount_eth <= 0:
            available_dst_tokens = [t for t in available_dst_tokens if t != 'ETH']
        available_dst_tokens = self._update_dst_tokens(available_dst_tokens, src_token)
        shuffle(available_dst_tokens)
        return available_dst_tokens

