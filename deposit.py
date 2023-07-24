import argparse
import json
import os
import threading
import traceback
from random import randint, uniform
from time import sleep
from typing import Dict

from eth_account import Account
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from starknet_py.hash.address import compute_address
from starknet_py.net.signer.stark_curve_signer import KeyPair
from web3 import Web3
from web3.middleware import (
    construct_sign_and_send_raw_middleware,
    geth_poa_middleware,
)
from database.models import StarknetAccountDeploy
from deploy import deploy_stark_account
from services import (
    FireFoxCreator,
    ProxyAgent,
    AccountParser,
    CLASS_HASH_ACCOUNT,
    IMPLEMENT_FUNC,
    CLASS_HASH_PROXY,
    TESTNET,
    logger,
)

PASSWORD = 'getfromenvfile'
ETH_RPC = os.getenv('ETH_RPC', 'https://eth.llamarpc.com')
if TESTNET:
    CONTRACT_ADDRESS = '0xc3511006C04EF1d78af4C8E0e74Ec18A6E64Ff9e'
else:
    CONTRACT_ADDRESS = '0xae0Ee0A63A2cE6BaeEFFE56e7714FB4EFE48D419'
CONTRACT_ABI = 'starknet_bridge.json'
DEPLOY_DELAY = 10


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
        default=1,
        type=float,
    )
    parser.add_argument(
        '--max-amount-swap',
        help='Максимальная сумма свапа в %',
        default=1.5,
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
        self.driver.find_element(
            By.XPATH, "//*[contains(text(), 'Account 1')]").click()

    def _save_secret_phrase(self):
        logger.info('Saving phrase')
        sleep(self.SLEEP)
        index = 1 if TESTNET else 0
        self.driver.find_elements(
            By.XPATH, value=f"//*[contains(text(),'Set up account')]")[index].click()
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
        if TESTNET:
            self.driver.find_element(
                By.XPATH, value=f"//*[contains(text(),'Yes')]").click()
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
        if TESTNET:
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
        gas_price = int(self.w3.eth.gas_price * 1.05)
        if gas_price <= self.max_gas_price:
            return gas_price
        raise ValueError(f'GasPrice is more than desired: {gas_price}')

    def save_db(self, amount):
        StarknetAccountDeploy.update(
            self.recipient,
            amount=amount,
            addressETH=self.sender.address,
        )

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
    try:
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
    finally:
        driver.quit()


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
