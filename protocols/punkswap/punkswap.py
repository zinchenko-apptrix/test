from eth_account.signers.local import LocalAccount
from web3.contract.contract import ContractFunctions
from web3.types import Wei

from eth_account import Account
from protocols.swap import SwapBase, SwapTransaction, SwapAgentBase
from services.exchanger import GeckoExchanger
from services.tokens import Token, WETH, TokenCreator
from services.transactions import TransactAgent
from services.utils import get_timestamp
from settings.config import PROJECT_DIR, MAIN_RPC


class PunkSwapExchanger(GeckoExchanger):
    POOLS = {
        'USDCETH': '0x6562e87944e4d6ccf9839c662db32e6b19f72cde',
        'USDTETH': '0xb12abb5bcb50c2aa6f1b54447046640010b33933',
        'USDCUSDT': '0x2307dbafed1464605e5cfc7fbc7ae761aa527f45',
    }


class PunkSwap(SwapBase[SwapTransaction]):
    CONTRACT = '0x26cB8660EeFCB2F7652e7796ed713c9fB8373f8e'
    ABI = f'{PROJECT_DIR}/protocols/punkswap/router.json'
    exchanger = PunkSwapExchanger

    def __init__(
        self,
        account: LocalAccount,
        src_token: Token,
        dst_token: Token,
        slippage: float,
    ):
        super().__init__(account, src_token, dst_token, slippage)
        if self.src_token.name == 'ETH':
            self.src_token.address = WETH
        if self.dst_token.name == 'ETH':
            self.dst_token.address = WETH
        self.router = self._get_contract()

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
        elif self.src_token.erc20 and self.dst_token.erc20:
            tx = self.router.functions.swapExactTokensForTokens(
                amount,
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


class PunkSwapAgent(SwapAgentBase[PunkSwap]):
    TOKENS = ['ETH', 'USDC', 'USDT']
    SWAP_CLASS = PunkSwap

    def _swap(self, txn, value, *args, **kwargs):
        return self._txn_agent.transact(txn, value)

    @property
    def name(self):
        return 'PunkSwap'


if __name__ == '__main__':
    account = Account.from_key('')
    src_token = TokenCreator.get('ETH', MAIN_RPC)
    dst_token = TokenCreator.get('USDC', MAIN_RPC)
    swaper = PunkSwap(
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
