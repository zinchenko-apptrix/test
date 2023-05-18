import argparse
import json
import logging
import random
import time
from logging.handlers import RotatingFileHandler

from aptos_sdk.account import Account
from eth_abi.packed import encode_packed
from web3 import Web3

from claim_usdc import claim_usdc
from database.binance.models import BinanceWithdrawal
from database.models import PolygonAptosBridge

logger = logging.getLogger('stgstacking')
file_handler = RotatingFileHandler(
    filename='logs.log',
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


START_CLAIM = 30
DST_AMOUNT_MIN = 5800000
DST_AMOUNT_MAX = 6200000

txn_explorer = {'MATIC': 'https://polygonscan.com/tx/'}
RPC = {'MATIC': 'https://polygon-rpc.com'}

APTOS_contract = '0x488863D609F3A673875a914fBeE7508a1DE45eC6'
APTOS_ABI = '[{"inputs":[{"internalType":"address","name":"_layerZeroEndpoint","type":"address"},{"internalType":"uint16","name":"_aptosChainId","type":"uint16"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"},{"indexed":false,"internalType":"uint256","name":"unlockTime","type":"uint256"}],"name":"EnableEmergencyWithdraw","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"indexed":false,"internalType":"uint64","name":"_nonce","type":"uint64"},{"indexed":false,"internalType":"bytes","name":"_payload","type":"bytes"},{"indexed":false,"internalType":"bytes","name":"_reason","type":"bytes"}],"name":"MessageFailed","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amountLD","type":"uint256"}],"name":"Receive","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"token","type":"address"}],"name":"RegisterToken","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"indexed":false,"internalType":"uint64","name":"_nonce","type":"uint64"},{"indexed":false,"internalType":"bytes32","name":"_payloadHash","type":"bytes32"}],"name":"RetryMessageSuccess","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token","type":"address"},{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"bytes32","name":"to","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"amountLD","type":"uint256"}],"name":"Send","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"aptosChainId","type":"uint16"}],"name":"SetAptosChainId","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"bridgeFeeBP","type":"uint256"}],"name":"SetBridgeBP","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bool","name":"paused","type":"bool"}],"name":"SetGlobalPause","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"localChainId","type":"uint16"}],"name":"SetLocalChainId","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"indexed":false,"internalType":"uint16","name":"_type","type":"uint16"},{"indexed":false,"internalType":"uint256","name":"_minDstGas","type":"uint256"}],"name":"SetMinDstGas","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"precrime","type":"address"}],"name":"SetPrecrime","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"token","type":"address"},{"indexed":false,"internalType":"bool","name":"paused","type":"bool"}],"name":"SetTokenPause","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_remoteChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_path","type":"bytes"}],"name":"SetTrustedRemote","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_remoteChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_remoteAddress","type":"bytes"}],"name":"SetTrustedRemoteAddress","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bool","name":"useCustomAdapterParams","type":"bool"}],"name":"SetUseCustomAdapterParams","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"weth","type":"address"}],"name":"SetWETH","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token","type":"address"},{"indexed":false,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amountLD","type":"uint256"}],"name":"WithdrawFee","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token","type":"address"},{"indexed":false,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amountLD","type":"uint256"}],"name":"WithdrawTVL","type":"event"},{"inputs":[],"name":"BP_DENOMINATOR","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"SHARED_DECIMALS","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"}],"name":"accruedFeeLD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"aptosChainId","outputs":[{"internalType":"uint16","name":"","type":"uint16"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"bridgeFeeBP","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"emergencyWithdrawEnabled","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"emergencyWithdrawTime","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bool","name":"enabled","type":"bool"}],"name":"enableEmergencyWithdraw","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"},{"internalType":"bytes","name":"","type":"bytes"},{"internalType":"uint64","name":"","type":"uint64"}],"name":"failedMessages","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"}],"name":"forceResumeReceive","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"},{"internalType":"uint16","name":"_chainId","type":"uint16"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"_configType","type":"uint256"}],"name":"getConfig","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_remoteChainId","type":"uint16"}],"name":"getTrustedRemoteAddress","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"globalPaused","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"}],"name":"isTrustedRemote","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"ld2sdRates","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"lzEndpoint","outputs":[{"internalType":"contract ILayerZeroEndpoint","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"internalType":"uint64","name":"_nonce","type":"uint64"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"lzReceive","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"},{"internalType":"uint16","name":"","type":"uint16"}],"name":"minDstGasLookup","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"internalType":"uint64","name":"_nonce","type":"uint64"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"nonblockingLzReceive","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"pausedTokens","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"precrime","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"components":[{"internalType":"address payable","name":"refundAddress","type":"address"},{"internalType":"address","name":"zroPaymentAddress","type":"address"}],"internalType":"struct LzLib.CallParams","name":"_callParams","type":"tuple"},{"internalType":"bytes","name":"_adapterParams","type":"bytes"}],"name":"quoteForSend","outputs":[{"internalType":"uint256","name":"nativeFee","type":"uint256"},{"internalType":"uint256","name":"zroFee","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"}],"name":"registerToken","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"internalType":"uint64","name":"_nonce","type":"uint64"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"retryMessage","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"_toAddress","type":"bytes32"},{"internalType":"uint256","name":"_amountLD","type":"uint256"},{"components":[{"internalType":"address payable","name":"refundAddress","type":"address"},{"internalType":"address","name":"zroPaymentAddress","type":"address"}],"internalType":"struct LzLib.CallParams","name":"_callParams","type":"tuple"},{"internalType":"bytes","name":"_adapterParams","type":"bytes"}],"name":"sendETHToAptos","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"bytes32","name":"_toAddress","type":"bytes32"},{"internalType":"uint256","name":"_amountLD","type":"uint256"},{"components":[{"internalType":"address payable","name":"refundAddress","type":"address"},{"internalType":"address","name":"zroPaymentAddress","type":"address"}],"internalType":"struct LzLib.CallParams","name":"_callParams","type":"tuple"},{"internalType":"bytes","name":"_adapterParams","type":"bytes"}],"name":"sendToAptos","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_aptosChainId","type":"uint16"}],"name":"setAptosChainId","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_bridgeFeeBP","type":"uint256"}],"name":"setBridgeFeeBP","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"},{"internalType":"uint16","name":"_chainId","type":"uint16"},{"internalType":"uint256","name":"_configType","type":"uint256"},{"internalType":"bytes","name":"_config","type":"bytes"}],"name":"setConfig","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bool","name":"_paused","type":"bool"}],"name":"setGlobalPause","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint16","name":"_packetType","type":"uint16"},{"internalType":"uint256","name":"_minGas","type":"uint256"}],"name":"setMinDstGas","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_precrime","type":"address"}],"name":"setPrecrime","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"}],"name":"setReceiveVersion","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"}],"name":"setSendVersion","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"bool","name":"_paused","type":"bool"}],"name":"setTokenPause","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_path","type":"bytes"}],"name":"setTrustedRemote","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_remoteChainId","type":"uint16"},{"internalType":"bytes","name":"_remoteAddress","type":"bytes"}],"name":"setTrustedRemoteAddress","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bool","name":"_useCustomAdapterParams","type":"bool"}],"name":"setUseCustomAdapterParams","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_weth","type":"address"}],"name":"setWETH","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"supportedTokens","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"}],"name":"trustedRemoteLookup","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"tvlSDs","outputs":[{"internalType":"uint64","name":"","type":"uint64"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"useCustomAdapterParams","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"weth","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"address","name":"_to","type":"address"}],"name":"withdrawEmergency","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"address","name":"_to","type":"address"},{"internalType":"uint256","name":"_amountLD","type":"uint256"}],"name":"withdrawFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"address","name":"_to","type":"address"},{"internalType":"uint64","name":"_amountSD","type":"uint64"}],"name":"withdrawTVL","outputs":[],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]'

matic_erc20_address = {
    'MATIC': '0x0000000000000000000000000000000000001010',
    'USDC': '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',
}
matic_erc20_abi = {
    'USDC': '[{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"account","type":"address"}],"name":"Blacklisted","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"newBlacklister","type":"address"}],"name":"BlacklisterChanged","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnerChanged","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"pauser","type":"address"}],"name":"Paused","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousPauser","type":"address"},{"indexed":true,"internalType":"address","name":"newPauser","type":"address"}],"name":"PauserChanged","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"},{"indexed":false,"internalType":"bytes","name":"data","type":"bytes"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"account","type":"address"}],"name":"UnBlacklisted","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"pauser","type":"address"}],"name":"Unpaused","type":"event"},{"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"blacklist","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"blacklister","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"bridgeBurn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_l1Address","type":"address"},{"internalType":"bytes","name":"_data","type":"bytes"}],"name":"bridgeInit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"bridgeMint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"changeOwner","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"gatewayAddress","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"},{"internalType":"uint8","name":"decimals","type":"uint8"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_gatewayAddress","type":"address"},{"internalType":"address","name":"_l1Address","type":"address"},{"internalType":"address","name":"owner","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"},{"internalType":"uint8","name":"decimals","type":"uint8"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"isBlacklisted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"l1Address","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"pause","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"paused","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"pauser","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"setPauser","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"transferAndCall","outputs":[{"internalType":"bool","name":"success","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"unBlacklist","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"unpause","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newBlacklister","type":"address"}],"name":"updateBlacklister","outputs":[],"stateMutability":"nonpayable","type":"function"}]',
}

network_erc20_addr = {'MATIC': matic_erc20_address}
network_erc20_abi = {'MATIC': matic_erc20_abi}


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с приватными ключами',
        default='accounts.tsv'
    )
    parser.add_argument(
        '--transfer-percent',
        help='Сколько баланса USDC переводим, %',
        type=int,
        default=10,
    )
    parser.add_argument(
        '--max-fee',
        help='Максимальная комиссия за перевод, WEI',
        type=int,
        default=1500000000000000000,
    )
    parser.add_argument(
        '--claim',
        help='Делать ли claim токенов на стороне APTOS',
        type=bool,
        default=False,
    )
    args = parser.parse_args()
    return (
        args.accounts_file,
        args.transfer_percent,
        args.max_fee,
        args.claim
    )


def get_contract(w3, contract_address, ABI=''):
    '''Одинаковый ABI для всех ERC20 токенов, в ликвидности могут быть другие ABI '''

    if ABI == '':
        ABI = json.loads('''[{"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"},{"internalType":"uint256","name":"_initialSupply","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint8","name":"decimals_","type":"uint8"}],"name":"setupDecimals","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]''')

    contract = w3.eth.contract(Web3.to_checksum_address(contract_address), abi=ABI)
    return contract


def add_gas(txn, w3):
    estimate = w3.eth.estimate_gas(txn)
    txn['gas'] = estimate
    return txn


def get_fee(contr, call_params, adapter_params, max_fee):
    while 1:
        fee = contr.functions.quoteForSend(call_params, adapter_params).call()[0]
        if fee <= max_fee:
            return fee
        logger.info(f'Комиссия за перевод: {fee}. Ожидание 60 сек')
        time.sleep(60)


def get_token_balance(w3, network, ticker, my_address):
    contract = get_contract(w3, network_erc20_addr[network][ticker])
    contract_func = contract.functions
    balance_wei = contract_func.balanceOf(my_address).call()  # in Wei
    token_decimals = contract_func.decimals().call()
    balance = balance_wei / 10 ** token_decimals
    return balance_wei, balance


def get_private_keys(addresses):
    """Get private keys from BinanceWithdrawal table"""
    withdrawals = BinanceWithdrawal.get_by_addresses(addresses)
    if len(withdrawals) != len(addresses):
        withdrawal_addresses = [w.address for w in withdrawals]
        lost_addr = [a for a in addresses if a not in withdrawal_addresses]
        logger.error(f'Не найдены приватные ключи для {lost_addr}')
    return [w.privateKey for w in withdrawals]


def get_adapter_params(to_address):
    dst_amount = random.randint(DST_AMOUNT_MIN, DST_AMOUNT_MAX)
    adapter_param3 = encode_packed(["uint16", "uint", "uint"], [2, 10000, dst_amount])
    return '0x' + adapter_param3.hex() + to_address[2:]


def generate_aptos_account(address, key) -> PolygonAptosBridge:
    acc = Account.generate()
    db_obj = PolygonAptosBridge.create(
        addressPolygon=address,
        privateKeyPolygon=key,
        addressAptos=acc.address().hex(),
        privateKeyAptos=acc.private_key.hex()
    )
    return db_obj


def get_balances(account, max_fee):
    usdc_balance_wei, _ = get_token_balance(
        w3, network, 'USDC', account.address
    )
    if usdc_balance_wei < 0:
        logger.error(f'{account.address} | На балансе нет USDC')
        raise ValueError(f'{account.address} | На балансе нет USDC')
    matic_balance_wei, _ = get_token_balance(
        w3, network, 'MATIC', account.address
    )
    if max_fee > matic_balance_wei:
        logger.error(f'{account.address} | Баланс MATIC меньше чем max fee')
        raise ValueError(f'{account.address} | Баланс MATIC меньше чем max fee')
    return usdc_balance_wei, matic_balance_wei


def approve_contract(w3, private_key, network, adr_dict, my_address):
    try:
        approve_amount = 2 ** 256 - 1
        contract = get_contract(w3, adr_dict['to_adr'])
        allowance = contract.functions.allowance(my_address, adr_dict['spender_adr']).call()
        if allowance == approve_amount:
            return True
        contract_txn = contract.functions.approve(adr_dict['spender_adr'], approve_amount)\
            .build_transaction({
                'from': my_address,
                'value': 0,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(my_address),
            })
        add_gas(contract_txn, w3)
        signed_txn = w3.eth.account.sign_transaction(contract_txn, private_key)
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_text = txn_hash.hex()
        w3.eth.wait_for_transaction_receipt(txn_hash)
        logger.info(f"{my_address} | УСПЕШНО апрув {adr_dict['to_ticker']} tx {txn_explorer[network]}{txn_text}")
        time.sleep(20)
        return True
    except Exception as error:
        logger.error(f"{my_address} | НЕУДАЧНО апрув {adr_dict['to_ticker']} | {error}")
        return False


def send_to_aptos(w3, private_key, my_address, amount, max_fee):
    try:
        contr = get_contract(w3, APTOS_contract, APTOS_ABI)
        token_address = w3.to_checksum_address(matic_erc20_address['USDC'])
        aptos_account = generate_aptos_account(my_address, private_key)
        call_params = (my_address, '0x0000000000000000000000000000000000000000')
        adapter_params = get_adapter_params(aptos_account.addressAptos)
        fee = get_fee(contr, call_params, adapter_params, max_fee)

        contract_txn = contr.functions.sendToAptos(
            token_address,
            aptos_account.addressAptos,
            amount,
            call_params,
            adapter_params
        ).build_transaction({
            'from': my_address,
            'value': fee,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(my_address)
        })
        signed_txn = w3.eth.account.sign_transaction(contract_txn, private_key)
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        aptos_account.set_polygon_txn(txn_hash.hex())
        w3.eth.wait_for_transaction_receipt(txn_hash)
        aptos_account.set_amount(amount)
        logger.info(f"{my_address} | УСПЕШНО отправка {amount / 10**8} USDC  tx {txn_explorer[network]}{txn_hash.hex()}")
    except Exception as error:
        logger.error(f"{my_address} | НЕУДАЧНО отправка USDC | {error}")


def bridge_to_aptos(w3, private_key, network, max_fee):
    try:
        account = w3.eth.account.from_key(private_key)
        usdc_balance_wei, _ = get_balances(account, max_fee)
        amount = int(usdc_balance_wei * percent / 100)
        aprove_adr_dict = {
            'to_ticker': 'USDC',
            'to_adr': Web3.to_checksum_address(network_erc20_addr[network]['USDC']),
            'spender_adr': APTOS_contract,
        }
        approved = approve_contract(w3, private_key, network, aprove_adr_dict, account.address)
        if approved:
            send_to_aptos(w3, private_key, account.address, amount, max_fee)
    except BaseException as error:
        logger.error(f'{private_key} | {error}')


if __name__ == '__main__':
    file, percent, max_fee, claim = parse_args()
    print(file, percent, claim)
    network = 'MATIC'
    with open(file, "r") as f:
        addresses = [row.strip() for row in f]
    keys_list = get_private_keys(addresses)
    w3 = Web3(Web3.HTTPProvider(RPC[network]))

    for private_key in keys_list:
        bridge_to_aptos(w3, private_key, network, max_fee)

    if claim:
        print(f'Claim начнется через {START_CLAIM} минут')
        time.sleep(START_CLAIM * 60)
        for address in addresses:
            db_obj = PolygonAptosBridge.get_by_polygon_address(address=address, amount=True)
            if not db_obj:
                logger.info(f'{addresses} | не найден в таблице PolygonAptosBridge. Либо claim уже выполнен или amount = 0')
                continue
            claim_usdc(db_obj, logger)
