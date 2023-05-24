import argparse
import csv
import logging
import os
import random
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests
from web3 import Web3, HTTPProvider, Account
from web3.middleware import geth_poa_middleware, construct_sign_and_send_raw_middleware

from database.binance.models import BinanceWithdrawal
from database.models import TraderJoeSwap

AVALANCHE_RPC = os.getenv('AVALANCHE_RPC', 'https://api.avax.network/ext/bc/C/rpc')
SWAP_CONTRACT_ADDRESS = '0xb4315e873dBcf96Ffd0acd8EA43f689D8c20fB30'
SWAP_CONTRACT_ABI = '[{"inputs":[{"internalType":"contract ILBFactory","name":"factory","type":"address"},{"internalType":"contract IJoeFactory","name":"factoryV1","type":"address"},{"internalType":"contract ILBLegacyFactory","name":"legacyFactory","type":"address"},{"internalType":"contract ILBLegacyRouter","name":"legacyRouter","type":"address"},{"internalType":"contract IWNATIVE","name":"wnative","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"AddressHelper__CallFailed","type":"error"},{"inputs":[],"name":"AddressHelper__NonContract","type":"error"},{"inputs":[],"name":"JoeLibrary__InsufficientAmount","type":"error"},{"inputs":[],"name":"JoeLibrary__InsufficientLiquidity","type":"error"},{"inputs":[{"internalType":"uint256","name":"amountSlippage","type":"uint256"}],"name":"LBRouter__AmountSlippageBPTooBig","type":"error"},{"inputs":[{"internalType":"uint256","name":"amountXMin","type":"uint256"},{"internalType":"uint256","name":"amountX","type":"uint256"},{"internalType":"uint256","name":"amountYMin","type":"uint256"},{"internalType":"uint256","name":"amountY","type":"uint256"}],"name":"LBRouter__AmountSlippageCaught","type":"error"},{"inputs":[{"internalType":"uint256","name":"id","type":"uint256"}],"name":"LBRouter__BinReserveOverflows","type":"error"},{"inputs":[],"name":"LBRouter__BrokenSwapSafetyCheck","type":"error"},{"inputs":[{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"currentTimestamp","type":"uint256"}],"name":"LBRouter__DeadlineExceeded","type":"error"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"LBRouter__FailedToSendNATIVE","type":"error"},{"inputs":[{"internalType":"uint256","name":"idDesired","type":"uint256"},{"internalType":"uint256","name":"idSlippage","type":"uint256"}],"name":"LBRouter__IdDesiredOverflows","type":"error"},{"inputs":[{"internalType":"int256","name":"id","type":"int256"}],"name":"LBRouter__IdOverflows","type":"error"},{"inputs":[{"internalType":"uint256","name":"activeIdDesired","type":"uint256"},{"internalType":"uint256","name":"idSlippage","type":"uint256"},{"internalType":"uint256","name":"activeId","type":"uint256"}],"name":"LBRouter__IdSlippageCaught","type":"error"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"uint256","name":"amountOut","type":"uint256"}],"name":"LBRouter__InsufficientAmountOut","type":"error"},{"inputs":[{"internalType":"address","name":"wrongToken","type":"address"}],"name":"LBRouter__InvalidTokenPath","type":"error"},{"inputs":[{"internalType":"uint256","name":"version","type":"uint256"}],"name":"LBRouter__InvalidVersion","type":"error"},{"inputs":[],"name":"LBRouter__LengthsMismatch","type":"error"},{"inputs":[{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"}],"name":"LBRouter__MaxAmountInExceeded","type":"error"},{"inputs":[],"name":"LBRouter__NotFactoryOwner","type":"error"},{"inputs":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint256","name":"binStep","type":"uint256"}],"name":"LBRouter__PairNotCreated","type":"error"},{"inputs":[],"name":"LBRouter__SenderIsNotWNATIVE","type":"error"},{"inputs":[{"internalType":"uint256","name":"id","type":"uint256"}],"name":"LBRouter__SwapOverflows","type":"error"},{"inputs":[{"internalType":"uint256","name":"excess","type":"uint256"}],"name":"LBRouter__TooMuchTokensIn","type":"error"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256","name":"reserve","type":"uint256"}],"name":"LBRouter__WrongAmounts","type":"error"},{"inputs":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint256","name":"amountX","type":"uint256"},{"internalType":"uint256","name":"amountY","type":"uint256"},{"internalType":"uint256","name":"msgValue","type":"uint256"}],"name":"LBRouter__WrongNativeLiquidityParameters","type":"error"},{"inputs":[],"name":"LBRouter__WrongTokenOrder","type":"error"},{"inputs":[],"name":"TokenHelper__TransferFailed","type":"error"},{"inputs":[{"components":[{"internalType":"contract IERC20","name":"tokenX","type":"address"},{"internalType":"contract IERC20","name":"tokenY","type":"address"},{"internalType":"uint256","name":"binStep","type":"uint256"},{"internalType":"uint256","name":"amountX","type":"uint256"},{"internalType":"uint256","name":"amountY","type":"uint256"},{"internalType":"uint256","name":"amountXMin","type":"uint256"},{"internalType":"uint256","name":"amountYMin","type":"uint256"},{"internalType":"uint256","name":"activeIdDesired","type":"uint256"},{"internalType":"uint256","name":"idSlippage","type":"uint256"},{"internalType":"int256[]","name":"deltaIds","type":"int256[]"},{"internalType":"uint256[]","name":"distributionX","type":"uint256[]"},{"internalType":"uint256[]","name":"distributionY","type":"uint256[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"address","name":"refundTo","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"struct ILBRouter.LiquidityParameters","name":"liquidityParameters","type":"tuple"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountXAdded","type":"uint256"},{"internalType":"uint256","name":"amountYAdded","type":"uint256"},{"internalType":"uint256","name":"amountXLeft","type":"uint256"},{"internalType":"uint256","name":"amountYLeft","type":"uint256"},{"internalType":"uint256[]","name":"depositIds","type":"uint256[]"},{"internalType":"uint256[]","name":"liquidityMinted","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"components":[{"internalType":"contract IERC20","name":"tokenX","type":"address"},{"internalType":"contract IERC20","name":"tokenY","type":"address"},{"internalType":"uint256","name":"binStep","type":"uint256"},{"internalType":"uint256","name":"amountX","type":"uint256"},{"internalType":"uint256","name":"amountY","type":"uint256"},{"internalType":"uint256","name":"amountXMin","type":"uint256"},{"internalType":"uint256","name":"amountYMin","type":"uint256"},{"internalType":"uint256","name":"activeIdDesired","type":"uint256"},{"internalType":"uint256","name":"idSlippage","type":"uint256"},{"internalType":"int256[]","name":"deltaIds","type":"int256[]"},{"internalType":"uint256[]","name":"distributionX","type":"uint256[]"},{"internalType":"uint256[]","name":"distributionY","type":"uint256[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"address","name":"refundTo","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"struct ILBRouter.LiquidityParameters","name":"liquidityParameters","type":"tuple"}],"name":"addLiquidityNATIVE","outputs":[{"internalType":"uint256","name":"amountXAdded","type":"uint256"},{"internalType":"uint256","name":"amountYAdded","type":"uint256"},{"internalType":"uint256","name":"amountXLeft","type":"uint256"},{"internalType":"uint256","name":"amountYLeft","type":"uint256"},{"internalType":"uint256[]","name":"depositIds","type":"uint256[]"},{"internalType":"uint256[]","name":"liquidityMinted","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"contract IERC20","name":"tokenX","type":"address"},{"internalType":"contract IERC20","name":"tokenY","type":"address"},{"internalType":"uint24","name":"activeId","type":"uint24"},{"internalType":"uint16","name":"binStep","type":"uint16"}],"name":"createLBPair","outputs":[{"internalType":"contract ILBPair","name":"pair","type":"address"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"getFactory","outputs":[{"internalType":"contract ILBFactory","name":"lbFactory","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract ILBPair","name":"pair","type":"address"},{"internalType":"uint256","name":"price","type":"uint256"}],"name":"getIdFromPrice","outputs":[{"internalType":"uint24","name":"","type":"uint24"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getLegacyFactory","outputs":[{"internalType":"contract ILBLegacyFactory","name":"legacyLBfactory","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getLegacyRouter","outputs":[{"internalType":"contract ILBLegacyRouter","name":"legacyRouter","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract ILBPair","name":"pair","type":"address"},{"internalType":"uint24","name":"id","type":"uint24"}],"name":"getPriceFromId","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract ILBPair","name":"pair","type":"address"},{"internalType":"uint128","name":"amountOut","type":"uint128"},{"internalType":"bool","name":"swapForY","type":"bool"}],"name":"getSwapIn","outputs":[{"internalType":"uint128","name":"amountIn","type":"uint128"},{"internalType":"uint128","name":"amountOutLeft","type":"uint128"},{"internalType":"uint128","name":"fee","type":"uint128"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract ILBPair","name":"pair","type":"address"},{"internalType":"uint128","name":"amountIn","type":"uint128"},{"internalType":"bool","name":"swapForY","type":"bool"}],"name":"getSwapOut","outputs":[{"internalType":"uint128","name":"amountInLeft","type":"uint128"},{"internalType":"uint128","name":"amountOut","type":"uint128"},{"internalType":"uint128","name":"fee","type":"uint128"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getV1Factory","outputs":[{"internalType":"contract IJoeFactory","name":"factoryV1","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getWNATIVE","outputs":[{"internalType":"contract IWNATIVE","name":"wnative","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"contract IERC20","name":"tokenX","type":"address"},{"internalType":"contract IERC20","name":"tokenY","type":"address"},{"internalType":"uint16","name":"binStep","type":"uint16"},{"internalType":"uint256","name":"amountXMin","type":"uint256"},{"internalType":"uint256","name":"amountYMin","type":"uint256"},{"internalType":"uint256[]","name":"ids","type":"uint256[]"},{"internalType":"uint256[]","name":"amounts","type":"uint256[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidity","outputs":[{"internalType":"uint256","name":"amountX","type":"uint256"},{"internalType":"uint256","name":"amountY","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract IERC20","name":"token","type":"address"},{"internalType":"uint16","name":"binStep","type":"uint16"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountNATIVEMin","type":"uint256"},{"internalType":"uint256[]","name":"ids","type":"uint256[]"},{"internalType":"uint256[]","name":"amounts","type":"uint256[]"},{"internalType":"address payable","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityNATIVE","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountNATIVE","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactNATIVEForTokens","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactNATIVEForTokensSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinNATIVE","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address payable","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForNATIVE","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinNATIVE","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address payable","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForNATIVESupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokensSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapNATIVEForExactTokens","outputs":[{"internalType":"uint256[]","name":"amountsIn","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountNATIVEOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address payable","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactNATIVE","outputs":[{"internalType":"uint256[]","name":"amountsIn","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"components":[{"internalType":"uint256[]","name":"pairBinSteps","type":"uint256[]"},{"internalType":"enum ILBRouter.Version[]","name":"versions","type":"uint8[]"},{"internalType":"contract IERC20[]","name":"tokenPath","type":"address[]"}],"internalType":"struct ILBRouter.Path","name":"path","type":"tuple"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactTokens","outputs":[{"internalType":"uint256[]","name":"amountsIn","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract IERC20","name":"token","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"sweep","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract ILBToken","name":"lbToken","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256[]","name":"ids","type":"uint256[]"},{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"name":"sweepLBToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]'
BTC_CONTRACT_ADDRESS = '0x152b9d0FdC40C096757F570A51E494bd4b943E50'
BTC_CONTRACT_ABI = '[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"AddSupportedChainId","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"newBridgeRoleAddress","type":"address"}],"name":"MigrateBridgeRole","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"address","name":"feeAddress","type":"address"},{"indexed":false,"internalType":"uint256","name":"feeAmount","type":"uint256"},{"indexed":false,"internalType":"bytes32","name":"originTxId","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"originOutputIndex","type":"uint256"}],"name":"Mint","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"Unwrap","type":"event"},{"inputs":[{"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"addSupportedChainId","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burnFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"chainIds","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newBridgeRoleAddress","type":"address"}],"name":"migrateBridgeRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address","name":"feeAddress","type":"address"},{"internalType":"uint256","name":"feeAmount","type":"uint256"},{"internalType":"bytes32","name":"originTxId","type":"bytes32"},{"internalType":"uint256","name":"originOutputIndex","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"unwrap","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
EXPLORER = 'https://snowtrace.io/tx/'


logger = logging.getLogger('buy_btc')
file_handler = RotatingFileHandler(
    filename='buy_btc.log',
    maxBytes=1024 * 1024 * 5,  # 5 MB
    backupCount=10,
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


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с адресами кошельков',
        default='accounts.tsv'
    )
    parser.add_argument(
        '--min-amount',
        help='Минимальная сумма покупки AVAX',
        default=0.0001,
        type=float,
    )
    parser.add_argument(
        '--max-amount',
        help='Максимальная сумма покупки AVAX',
        type=float,
        default=0.0001,
    )
    parser.add_argument(
        '--max-gas-price',
        help='Максимальная стоимость газа',
        type=int,
        default=39795261241,
    )
    parser.add_argument(
        '--min-delay',
        help='Минимальная задержка между переводами, с',
        type=int,
        default=3,
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
        args.min_amount,
        args.max_amount,
        args.max_gas_price,
        args.min_delay,
        args.max_delay,
    )


class TraderJoe:
    def __init__(
        self,
        swap_contract: dict,
        dst_contract: dict,
        rpc: str,
        max_gas_price: int,
    ):
        self.w3 = Web3(HTTPProvider(rpc))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.swap_contract = self.w3.eth.contract(
            address=swap_contract['address'], abi=swap_contract['abi']
        )
        self.dst_contract = self.w3.eth.contract(
            address=dst_contract['address'], abi=dst_contract['abi']
        )
        self.max_gas_price = max_gas_price
        self.account = None
        self.dst_balance = None

        self.dst_decimals = 8
        self.minimal_dst_percent = 0.9
        self.waiting_receipt_timeout = 10 * 60
        self.gas_price_timeout = 60
        self.symbol_pair = 'AVAXBTC'

    def swap(self, amount: float):
        amount_min = self._get_amount_min(amount)
        path = ([0], [0], ['0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7', '0x152b9d0FdC40C096757F570A51E494bd4b943E50'])
        deadline = int(datetime.now().timestamp() + 30 * 60)
        txn = self.swap_contract.functions.swapExactNATIVEForTokens(
            amount_min,
            path,
            self.account.address,
            deadline
        )
        txn_data = self._get_txn_data(txn, amount)
        txn_hash = txn.transact(txn_data)
        self.w3.eth.wait_for_transaction_receipt(
            txn_hash, timeout=self.waiting_receipt_timeout
        )
        logger.info(f'{self.account.address} || SUCCESS {amount} AVAX to BTC {EXPLORER}{txn_hash.hex()}')
        self._create_log(amount)

    def set_account(self, private_key):
        account = Account.from_key(private_key)
        self.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
        self.account = account
        self.dst_balance = self.dst_contract.functions.balanceOf(account.address).call()

    def _get_txn_data(self, txn, amount: float):
        txn_data = {
            'from': self.account.address,
            'value': self.w3.to_wei(amount, 'ether'),
            'gasPrice': self._get_gas_price(),
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        }
        txn_data['gas'] = txn.estimate_gas(txn_data)
        return txn_data

    def _create_log(self, amount: float):
        dst_balance = self.dst_contract.functions.balanceOf(self.account.address).call()
        TraderJoeSwap.create(
            address=self.account.address,
            privateKey=self.account._private_key.hex(),
            amount_in=amount,
            amount_out=(dst_balance - self.dst_balance) / 10**self.dst_decimals
        )

    def _get_gas_price(self):
        for _ in range(10):
            gas_price = self.w3.eth.gas_price
            if gas_price <= self.max_gas_price:
                return gas_price
            logger.warning(f'{self.account.address} || Gas price too high - {gas_price}')
            time.sleep(60)
        raise ValueError('Gas price too high')

    def _get_amount_min(self, amount: float):
        response = requests.get(
            f'https://api.binance.com/api/v3/trades?symbol={self.symbol_pair}'
        )
        rate = round(float(response.json()[0]['price']), 5)
        amount_dst = int(rate * amount * 10 ** self.dst_decimals)
        minimal_dst = int(amount_dst * self.minimal_dst_percent)
        if minimal_dst <= 0:
            raise ValueError('Not enough AVAX')
        return minimal_dst


class AccountParser:
    """
    Парсинг приватных ключей из таблицы выводов Binance по адресам из файла
    """
    def __init__(self, file_path: str, rpc):
        self.file_path = file_path
        self.accounts = None
        self.w3 = Web3(HTTPProvider(endpoint_uri=rpc))
        self.addresses = self.get_addresses_from_file()

    def get_wallets(self):
        """Get private keys from BinanceWithdrawal table"""
        if self.accounts is not None:
            return self.accounts
        withdrawals = BinanceWithdrawal.get_by_addresses(self.addresses)
        if len(withdrawals) != len(self.addresses):
            withdrawal_addresses = [w.address for w in withdrawals]
            lost_addr = [a for a in self.addresses if a not in withdrawal_addresses]
            logger.error(f'Private keys are not found {lost_addr}')
        return [(w.address, w.privateKey) for w in withdrawals if self.check_private_key(w)]

    def check_private_key(self, withdrawal: BinanceWithdrawal):
        try:
            acc = self.w3.eth.account.from_key(withdrawal.privateKey)
            if acc.address == withdrawal.address:
                return True
            logger.error(f'Wrong private key: {withdrawal.address}')
        except Exception as e:
            logger.error(f'{e} {withdrawal.address}')

    def get_addresses_from_file(self):
        self.validate_file()
        with open(self.file_path) as f:
            reader = csv.reader(f, delimiter='\t')
            lines = [a for a in reader]
        if len(lines[0]) > 1:
            self.accounts = [
                (a[0], a[1]) for a in lines
                if self.check_private_key(
                    BinanceWithdrawal(address=a[0], privateKey=a[1])
                )
            ]
        return [a[0] for a in lines]

    def validate_file(self):
        f = self.file_path
        if not os.path.isfile(f):
            raise ValueError(f'File not found: {f}')
        if not f.endswith('.tsv') and not f.endswith('.csv'):
            raise ValueError(f'Wrong file format: {f}')


if __name__ == '__main__':
    (
        accounts_file,
        min_amount,
        max_amount,
        max_gas_price,
        min_delay,
        max_delay,
    ) = parse_args()
    parser = AccountParser(file_path=accounts_file, rpc=AVALANCHE_RPC)
    wallets = parser.get_wallets()
    trader = TraderJoe(
        swap_contract={'address': SWAP_CONTRACT_ADDRESS, 'abi': SWAP_CONTRACT_ABI},
        dst_contract={'address': BTC_CONTRACT_ADDRESS, 'abi': BTC_CONTRACT_ABI},
        rpc=AVALANCHE_RPC,
        max_gas_price=max_gas_price
    )
    for address, key in wallets:
        try:
            trader.set_account(key)
            amount = random.uniform(min_amount, max_amount)
            trader.swap(amount)
            if address != wallets[-1][0]:
                time.sleep(random.randint(min_delay, max_delay))
        except BaseException as error:
            logger.error(f'{address} || {error}')
