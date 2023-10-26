import typing
from dataclasses import dataclass, field
from random import randint, uniform, shuffle

from protocols import PROTOCOLS
from protocols.base import IProtocol

if typing.TYPE_CHECKING:
    from services.account import Wallet


@dataclass
class Step:
    protocol_names: list[str]
    tokens: list[str]
    min_balance_usd: float
    min_remains_eth_wei: float
    unique_protocols: bool
    toeth: bool
    amount_eth: float
    amount_stable: float
    slippage_eth: float
    slippage_stable: float
    max_gas_price: int
    max_gas_price_l1: int
    max_gas_limit: int
    size: str = 'Big'
    protocols: list[typing.Type[IProtocol]] = field(default_factory=list)

    def __post_init__(self):
        self.protocols = [PROTOCOLS[p] for p in self.protocol_names]


class StepGenerator:
    def __init__(
        self,
        wallets: list['Wallet'],
    ):
        self.wallets = wallets

    def generate(
        self,
        min_balance_usd: float,
        min_remains: float,
        tokens: list[str],
        protocols: list[str],
        unique: bool,
        toeth: bool,
        min_count_txn: int,
        max_count_txn: int,
        min_amount_eth: float,
        max_amount_eth: float,
        min_amount_stables: float,
        max_amount_stables: float,
        small_transactions_percent: float,
        small_protocols: list[str],
        small_tokens: list[str],
        small_amount_percent: float,
        small_min_balance: float,
        small_transactions_slippage_eth: float,
        small_transactions_slippage_stable: float,
        max_gas_price: int,
        max_gas_price_l1: int,
        max_gas_limit: int,
        slippage_eth: int,
        slippage_stable: int,
    ):
        steps = []
        for wallet in self.wallets:
            if unique:
                big_txn_count = len(protocols)
            elif toeth:
                not_eth_tokens = [t for t in tokens if t != 'ETH']
                big_txn_count = len(not_eth_tokens)
            else:
                big_txn_count = randint(min_count_txn, max_count_txn)
            common_params = {
                'unique_protocols': unique,
                'toeth': toeth,
                'min_remains_eth_wei': min_remains,
                'max_gas_price': max_gas_price,
                'max_gas_price_l1': max_gas_price_l1,
                'max_gas_limit': max_gas_limit,
            }
            for i in range(big_txn_count):
                steps.append(
                    Step(
                        protocol_names=protocols,
                        tokens=tokens,
                        amount_eth=uniform(min_amount_eth, max_amount_eth),
                        amount_stable=uniform(min_amount_stables, max_amount_stables),
                        slippage_eth=slippage_eth,
                        slippage_stable=slippage_stable,
                        min_balance_usd=min_balance_usd,
                        size='Big',
                        **common_params
                    )
                )
            small_txn_count = round(big_txn_count * small_transactions_percent / 100)
            common_params.update({'toeth': False, 'unique_protocols': False})
            for j in range(small_txn_count):
                steps.append(
                    Step(
                        protocol_names=small_protocols,
                        tokens=small_tokens,
                        amount_eth=small_amount_percent,
                        amount_stable=small_amount_percent,
                        slippage_eth=small_transactions_slippage_eth,
                        slippage_stable=small_transactions_slippage_stable,
                        min_balance_usd=small_min_balance,
                        size='Small',
                        **common_params,
                    )
                )
            shuffle(steps)
            wallet.steps = steps
