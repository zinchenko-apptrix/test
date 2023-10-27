from web3.contract.contract import ContractFunctions
from web3.types import Wei

from eth_account import Account
from protocols.swap import SwapBase, SwapTransaction, SwapAgentBase
from services.exchanger import GeckoExchanger
from services.tokens import TokenCreator
from services.transactions import TransactAgent
from services.utils import get_timestamp
from settings.config import PROJECT_DIR, MAIN_RPC


class ScrollSwapExchanger(GeckoExchanger):
    POOLS = {
        'USDTETH': '0xe3c46d28c23007b0bff7bb58471c81312c0a8690',
    }


class ScrollSwap(SwapBase[SwapTransaction]):
    CONTRACT = '0xEfEb222F8046aAa032C56290416C3192111C0085'
    ABI = f'{PROJECT_DIR}/protocols/punkswap/router.json'
    exchanger = ScrollSwapExchanger

    def _get_txn(self, amount: Wei) -> tuple[ContractFunctions, int]:
        dst_amount = self._get_min_dst(amount)
        common_params = [
            [self.src_token.address, self.dst_token.address],
            self.account.address,
            get_timestamp(),
        ]
        if self.src_token.name == 'ETH':
            tx = self.router.functions.swapExactETHForTokens(
                dst_amount,
                *common_params,
            )
        else:
            tx = self.router.functions.swapExactTokensForETH(
                amount,
                dst_amount,
                *common_params,
            )
        return tx, dst_amount


class ScrollSwapAgent(SwapAgentBase[ScrollSwap]):
    TOKENS = ['ETH', 'USDT']
    SWAP_CLASS = ScrollSwap

    def _swap(self, txn, value: Wei, *args, **kwargs):
        return self._txn_agent.transact(txn, value)

    @property
    def name(self):
        return 'ScrollSwap'


if __name__ == '__main__':
    account = Account.from_key('')
    src_token = TokenCreator.get('ETH', MAIN_RPC)
    dst_token = TokenCreator.get('USDT', MAIN_RPC)
    swaper = ScrollSwap(
        account=account,
        src_token=src_token,
        dst_token=dst_token,
        slippage=1
    )
    txn_agent = TransactAgent(
        account=account,
        max_gas_limit=100000000000000,
        max_gas_price=10000000000000000000000,
        max_gas_price_l1=100000000000000000,
    )
    value = Wei(int(0.0001*10**18))
    swap_txn = swaper.swap(value)
    # approve_txn = check_allowance(src_token, account, swaper.CONTRACT, value)
    # if approve_txn:
    #     txn_agent.transact(approve_txn)
    txn_agent.transact(swap_txn.txn, value)
