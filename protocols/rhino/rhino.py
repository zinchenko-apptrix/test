from time import sleep

from web3 import Web3

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from eth_account.account import Account

from database.models import RhinoBridge
from protocols.metamask import MetaMaskLoader, FireFoxCreator, _wait_and_open_window, Network, \
    is_button_available
from services.logger import logger
from services.proxy import ProxyAgent
from services.transactions import get_suitable_gas_price
from settings.config import MAIN_RPC, SLEEP, SHORT_SLEEP, ARBITRUM_RPC


def wait_gas_price(max_gas_price_l1, max_gas_price_l2):
    w3_eth = Web3(Web3.HTTPProvider(MAIN_RPC))
    get_suitable_gas_price(max_gas_price_l1, w3_eth)
    w3_scroll = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
    get_suitable_gas_price(max_gas_price_l2, w3_scroll)


class RhinoMarketBuyer:
    def __init__(
        self,
        driver: WebDriver,
        private_key: str,
        address: str,
        url: str,
        max_gas_price_l1: int,
        max_gas_price_l2: int,
    ):
        self.driver = driver
        self.private_key = private_key
        self.address = address
        self.url = url
        self.max_gas_price_l1 = max_gas_price_l1
        self.max_gas_price_l2 = max_gas_price_l2
        self.action = ActionChains(self.driver)

    def bridge(self, amount: float = 0, max_balance: bool = False):
        self.driver.get(self.url)
        self.driver.set_window_size(1920, 1280)
        self._close_popups()
        self._connect_walelt()
        self._authenticate_wallet()
        bridged_amount, destination_amount = self._input_swap_amount(amount, max_balance)
        _wait_and_open_window(self.driver, 1)
        wait_gas_price(self.max_gas_price_l1, self.max_gas_price_l2)
        fee = self._sign_transaction()
        logger.info(f'{self.address} || SUCCESS. fee: {fee}')
        return bridged_amount, destination_amount, fee

    def _sign_transaction(self):
        confirm_btn = self.driver.find_element(
            By.XPATH, value="//button[contains(text(),'Confirm')]")
        if not is_button_available(confirm_btn):
            raise ValueError('Confirm button unavailable')
        fee = self.driver.find_elements(
            By.CLASS_NAME, value='currency-display-component__text')[4].text
        confirm_btn.click()
        sleep(SLEEP)
        self.driver.switch_to.window(self.driver.window_handles[0])
        return fee

    def _validate_input(self):
        error_element = self.driver.find_elements(By.XPATH, value='//div[@id="error-wrapper"]//div//p')
        if error_element:
            raise ValueError(error_element[0].text)

    def _input_swap_amount(self, amount: float = 0, max_balance: bool = False):
        self.driver.find_element(By.ID, value='deposit-input').click()
        self.driver.find_element(By.XPATH, value='//span[contains(text(), "ETH")]').click()
        max_swap_element = self.driver.find_element(
            By.XPATH, value='//button[@id="max-bridge"]//span')
        input_field = self.driver.find_element(By.ID, value='bridge-amount')
        if max_balance:
            sleep(SHORT_SLEEP)
            max_swap_element.click()
        else:
            input_field.send_keys(amount)
        input_amount = input_field.get_attribute("value")
        destination_amount = self.driver.find_element(
            By.ID, value='bridge-withdraw-amount'
        ).get_attribute('value')
        logger.info(f'{self.address} || bridging {input_amount}')
        sleep(SHORT_SLEEP)
        self.driver.find_element(By.ID, value='review-bridge').click()
        self._validate_input()
        sleep(SHORT_SLEEP * 2)
        try:
            self.driver.find_element(By.ID, value='bridge-funds').click()
        except BaseException:
            ...
        return input_amount, destination_amount

    def _authenticate_wallet(self):
        btn = self.driver.find_elements(By.ID, value='authentication-action')
        if not btn:
            return
        sleep(SHORT_SLEEP * 2)
        btn[0].click()
        _wait_and_open_window(self.driver, 1)
        self.driver.find_element(By.XPATH, value=f"//button[contains(text(),'Sign')]").click()
        sleep(SHORT_SLEEP)
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.driver.find_element(By.ID, value='unlock-key-action').click()
        _wait_and_open_window(self.driver, 1)
        self.driver.find_element(By.XPATH, value=f"//button[contains(text(),'Sign')]").click()
        sleep(SHORT_SLEEP)
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.driver.find_element(By.ID, value='authentication-completed-cta').click()

    def _connect_walelt(self):
        self.driver.find_element(
            By.XPATH, value='//span[contains(text(), "connect wallet")]').click()
        sleep(SHORT_SLEEP)
        self.driver.find_element(By.ID, value='metamask').click()
        _wait_and_open_window(self.driver, 1)
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Next')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Connect')]").click()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def _close_popups(self):
        cookies = self.driver.find_elements(By.ID, value='close-cookies')
        if cookies:
            sleep(SLEEP)
            cookies[0].click()


def bridge(
    wallet,
    max_gas_price_l2: int,
    max_gas_price_l1: int,
    amount: float = 0,
    proxy_address: str | None = None,
    max_balance: bool = False,
):
    ProxyAgent.reset_proxy()
    driver = FireFoxCreator(proxy_address).driver
    mm_loader = MetaMaskLoader(
        driver=driver,
        private_key=wallet.private_key,
        address=wallet.address,
        network=Network(
            name='Arbitrum',
            rpc='https://arb1.arbitrum.io/rpc',
            chain_id=42161,
            currency='ETH',
            explorer='https://arbiscan.io',
        )
    )
    mm_loader.connect_wallet()
    mm_loader.change_network()
    buyer = RhinoMarketBuyer(
        driver=driver,
        private_key=wallet.private_key,
        address=wallet.address,
        url='https://app.rhino.fi/bridge?token=ETH&chainOut=SCROLL',
        max_gas_price_l1=max_gas_price_l1,
        max_gas_price_l2=max_gas_price_l2
    )
    src_amount, dst_amount, fee = buyer.bridge(amount=amount, max_balance=max_balance)
    RhinoBridge.create(
        address=wallet.address,
        srcAmount=src_amount,
        dstAmount=dst_amount,
        fee=fee,
    )
