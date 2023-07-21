import argparse
import json
import logging
import os
import threading
import traceback
from logging.handlers import RotatingFileHandler
from random import randint, uniform
from time import sleep
from typing import Dict, List

from eth_account import Account
from starknet_py.net.account.account import Account as StarkAccount
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from starknet_py.hash.address import compute_address
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.networks import TESTNET, MAINNET
from starknet_py.net.signer.stark_curve_signer import KeyPair
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware, \
    geth_poa_middleware

from database.models import StarknetAccountDeploy
from services import FireFoxCreator, ProxyAgent, AccountParser

PASSWORD = 'getfromenvfile'
ETH_RPC = os.getenv('ETH_RPC', 'https://eth.llamarpc.com')
PRODUCTION = os.getenv('PRODUCTION', True)
CONTRACT_ADDRESS = '0xc3511006C04EF1d78af4C8E0e74Ec18A6E64Ff9e'
CONTRACT_ABI = 'starknet_bridge.json'
CLASS_HASH_PROXY = 0x025ec026985a3bf9d0cc1fe17326b245dfdc3ff89b8fde106542a3ea56c5a918
CLASS_HASH_ACCOUNT = 0x033434ad846cdd5f23eb73ff09fe6fddd568284a0fb7d1be20ee482f044dabe2
IMPLEMENT_FUNC = 215307247182100370520050591091822763712463273430149262739280891880522753123
DEPLOY_DELAY = 10
CLIENT = MAINNET if PRODUCTION else TESTNET
CHAIN = StarknetChainId.MAINNET if PRODUCTION else StarknetChainId.TESTNET


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


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--accounts-file',
        help='Файл CSV/TSV с адресами кошельков',
        default='accs.tsv'
    )
    parser.add_argument(
        '--proxies-file',
        help='Текстовый файл с прокси',
    )
    parser.add_argument(
        '--min-amount-swap',
        help='Минимальная сумма свапа в %',
        default=0.1,
        type=float,
    )
    parser.add_argument(
        '--max-amount-swap',
        help='Максимальная сумма свапа в %',
        default=0.2,
        type=float,
    )
    parser.add_argument(
        '--max-gas-limit',
        help='Максимальный gas limit в wei',
        default=1000000000000,
        type=int,
    )
    parser.add_argument(
        '--max-gas-price',
        help='Максимальная стоимость газа в wei',
        default=2000000000000,
        type=int,
    )
    parser.add_argument(
        '--max-fee-deploy',
        help='Максимальная комиссия за деплой аккаунта starknet, wei',
        default=1000000000000000,
        type=int,
    )
    parser.add_argument(
        '--min-delay',
        help='Минимальная задержка между переводами, с',
        type=int,
        default=1,
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
        args.proxies_file,
        args.min_amount_swap,
        args.max_amount_swap,
        args.max_gas_limit,
        args.max_gas_price,
        args.max_fee_deploy,
        args.min_delay,
        args.max_delay,
    )


def get_wallet_address(private_key: str):
    key_pair = KeyPair.from_private_key(int(private_key, 16))

    call_data = [
        int(CLASS_HASH_ACCOUNT),
        IMPLEMENT_FUNC,
        2,
        key_pair.public_key,
        0,
    ]

    address = compute_address(
        salt=key_pair.public_key,
        class_hash=CLASS_HASH_PROXY,
        constructor_calldata=call_data,
    )
    return hex(address)


class StarkWallet:
    MICRO_SLEEP = 0.5
    SLEEP = 2
    WAIT_PHRASE = 10

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def _create_wallet(self):
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Create a new wallet')]"
        ).click()
        check_box_inputs = self.driver.find_elements(
            By.XPATH, value=f"//*[contains(@class,'chakra-form')]"
        )
        for box in check_box_inputs:
            box.click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Continue')]"
        ).click()
        password_inputs = self.driver.find_elements(
            By.XPATH, value=f"//*[contains(@class,'chakra-input')]"
        )
        for password_input in password_inputs:
            password_input.send_keys(PASSWORD)
        sleep(self.MICRO_SLEEP)
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Create wallet')]"
        ).click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Finish')]"
        ).click()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def _switch_to_testnet(self):
        sleep(self.SLEEP)
        self.driver.find_element(
            By.XPATH, "//button//span[text()='Mainnet']/..").click()
        self.driver.find_element(By.XPATH, "//button[@data-index='1']").click()
        self.driver.find_element(
            By.XPATH, "//button[contains(text(), 'Create account')]").click()
        self.driver.find_element(
            By.XPATH, "//button[@aria-label='Standard Account']").click()

    def _save_secret_phrase(self):
        logger.info('Saving phrase')
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Set up account')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Save the recovery')]").click()
        sleep(self.WAIT_PHRASE)
        phrase_container = self.driver.find_element(
            By.XPATH, "//div[count(div) = 12]")
        word_elements = phrase_container.find_elements(By.XPATH, "./div")
        words = [word.text.split('\n')[1] for word in word_elements]
        if not all([word.isalpha() for word in words]) or len(words) != 12:
            raise ValueError('Phrase error')
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Continue')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Yes')]").click()
        sleep(self.MICRO_SLEEP)
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Yes')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Account 1')]").click()
        return ' '.join(words)

    def _get_private_key(self):
        logger.info('Exporting private key')
        self._open_private_key_block()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Export private key')]"
        ).click()
        password_input = self.driver.find_element(
            By.XPATH, "//input[@name='password']"
        )
        password_input.send_keys(PASSWORD)
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Export')]"
        ).click()
        return self.driver.find_element(
            By.XPATH, "//div[@data-testid='privateKey']//div"
        ).text

    def _open_private_key_block(self):
        for _ in range(2):
            self.driver.find_element(
                By.XPATH, "//button[@aria-label='Show settings']").click()
            button = self.driver.find_element(
                By.XPATH, "//button[@aria-label='Select Account 1']")
            sleep(self.MICRO_SLEEP)
            self.driver.execute_script("arguments[0].click();", button)
            sleep(self.MICRO_SLEEP)

    def save_db(self, phrase, key, address):
        StarknetAccountDeploy.create(
            addressStark=address,
            privateKey=key,
            phrase=phrase
        )

    def create_wallet(self):
        logger.info('Start creating wallet')
        self.driver.switch_to.window(self.driver.window_handles[1])
        extension_url = self.driver.current_url.replace(
            'onboarding/start', 'index.html'
        )
        self._create_wallet()
        self.driver.get(extension_url)
        self._switch_to_testnet()
        phrase = self._save_secret_phrase()
        key = self._get_private_key()
        address = get_wallet_address(key)
        self.save_db(phrase, key, address)
        logger.info(f'Starknet wallet is created : {address}')
        return key, address


class Bridge:
    def __init__(
        self,
        recipient_address,
        sender_key,
        rpc,
        max_gas_limit,
        max_gas_price
    ):
        self.recipient = recipient_address
        self.sender = Account.from_key(sender_key)
        self.w3 = Web3(Web3.HTTPProvider(rpc))
        self.max_gas_limit = max_gas_limit
        self.max_gas_price = max_gas_price
        self.contract = self.get_contract()
        self.set_account()

    def set_account(self):
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.w3.middleware_onion.add(
            construct_sign_and_send_raw_middleware(self.sender)
        )

    def get_contract(self):
        with open(CONTRACT_ABI) as file:
            return self.w3.eth.contract(
                address=CONTRACT_ADDRESS, abi=json.load(file)
            )

    def get_amount(self, percent: float) -> int:
        balance = self.w3.eth.get_balance(self.sender.address)
        return int(balance / 100 * percent)

    def _transact(self, txn, amount):
        txn_data = {
            'from': self.sender.address,
            'gasPrice': self.get_gas_price(),
            'nonce': self.w3.eth.get_transaction_count(self.sender.address),
            'value': amount,
        }
        txn_data['gas'] = self.get_gas(txn, txn_data)
        return txn.transact(txn_data)

    def get_gas(self, txn, txn_data: Dict) -> int:
        gas = txn.estimate_gas(txn_data)
        if gas <= self.max_gas_limit:
            return gas
        raise ValueError(f'Gas limit is more than desired: {gas}')

    def get_gas_price(self) -> int:
        gas_price = self.w3.eth.gas_price
        if gas_price <= self.max_gas_price:
            return gas_price
        raise ValueError(f'GasPrice is more than desired: {gas_price}')

    def save_db(self, amount):
        StarknetAccountDeploy.update(self.recipient, amount=amount)

    def send_eth(self, amount_percent: float):
        logger.info(f'{self.sender.address} || depositing')
        amount = self.get_amount(amount_percent)
        txn = self.contract.functions.deposit(
            amount - 1,
            int(self.recipient, 16)
        )
        txn_hash = self._transact(txn, amount)
        self.w3.eth.wait_for_transaction_receipt(txn_hash, timeout=240)
        self.save_db(amount / 10 ** 18)
        logger.info(f'{self.sender.address} || sent {amount / 10**18} ETH')


class Deployer:
    def __init__(self, address: int, private_key: int, max_fee: int):
        self.address = address
        self.max_fee = max_fee
        self.key_pair = KeyPair.from_private_key(private_key)

    def deploy(self):
        logger.info(f'{self.address} Deploying account')
        call_data = self.get_call_data()
        result = StarkAccount.deploy_account_sync(
            address=self.address,
            class_hash=CLASS_HASH_PROXY,
            salt=self.key_pair.public_key,
            key_pair=self.key_pair,
            client=GatewayClient(CLIENT),
            chain=CHAIN,
            constructor_calldata=call_data,
            max_fee=self.max_fee,
        )
        result.wait_for_acceptance_sync()
        logger.info(f'{self.address} || Account deployed')
        self.save_db()

    def save_db(self):
        StarknetAccountDeploy.update(
            address_stark=hex(self.address),
            deployed=True
        )

    def get_call_data(self) -> List:
        return [
            int(CLASS_HASH_ACCOUNT),
            IMPLEMENT_FUNC,
            2,
            self.key_pair.public_key,
            0,
        ]


def deploy_stark_account(address: str, stark_key: str, max_fee_deploy: int):
    try:
        deployer = Deployer(
            address=int(address, 16),
            private_key=int(stark_key, 16),
            max_fee=max_fee_deploy
        )
        deployer.deploy()
    except BaseException as error:
        logger.error(f'{address} deploy error: {error}')


def main(
    eth_address,
    eth_key,
    amount_percent,
    max_gas_limit,
    max_gas_price,
    max_fee_deploy,
    proxy_agent
):
    proxy = proxy_agent.get_proxy(eth_address)
    proxy_agent.reset_proxy()
    driver = FireFoxCreator(proxy).driver
    cr = StarkWallet(driver)
    stark_key, address = cr.create_wallet()

    proxy_agent.rotate(eth_address)
    bridge = Bridge(
        recipient_address=address,
        sender_key=eth_key,
        rpc=ETH_RPC,
        max_gas_limit=max_gas_limit,
        max_gas_price=max_gas_price,
    )
    bridge.send_eth(amount_percent)

    threading.Timer(
        DEPLOY_DELAY * 60,
        deploy_stark_account,
        args=(address, stark_key, max_fee_deploy)
    ).start()


if __name__ == '__main__':
    (
        accounts_file,
        proxies_file,
        min_amount_swap,
        max_amount_swap,
        max_gas_limit,
        max_gas_price,
        max_fee_deploy,
        min_delay,
        max_delay,
    ) = parse_args()
    proxy_agent = ProxyAgent(proxies_file)
    parser = AccountParser(accounts_file, ETH_RPC)
    wallets = parser.get_private_keys()

    for addr, key in wallets:
        try:
            amount_percent = uniform(min_amount_swap, max_amount_swap)
            main(
                addr,
                key,
                amount_percent,
                max_gas_limit,
                max_gas_price,
                max_fee_deploy,
                proxy_agent
            )
            sleep(randint(min_delay, max_delay))
        except BaseException as error:
            logger.error(traceback.format_exc())
            logger.error(f'{addr} || Error: {error}')
