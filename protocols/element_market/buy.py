import os.path
import traceback
from datetime import datetime
from time import sleep

from web3 import Web3
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
import seleniumwire.undetected_chromedriver.v2 as uc

from database.models import ScrollCombine
from database.other.models import Proxy
from protocols.base import IProtocol
from services.logger import logger
from services.proxy import ProxyAgent
from settings.config import (
    GAS_WAITING,
    PROJECT_DIR,
    SHORT_SLEEP,
    PASSWORD,
    SLEEP,
    MAIN_RPC, ELEMENT_MIN_PRICE, ELEMENT_MAX_PRICE,
)


URL = 'https://element.market/assets'


def _wait_and_open_window(driver, number_window: int):
    for _ in range(20):
        if len(driver.window_handles) >= number_window + 1:
            driver.switch_to.window(driver.window_handles[number_window])
            return
        sleep(SHORT_SLEEP)
    raise ValueError(f'Window not opening. Slow internet connection / Bad Proxy')


class ChromeCreator:

    def __init__(self, proxy=None):
        self.proxy = proxy
        self.driver = uc.Chrome(
            options=self.get_options(),
            seleniumwire_options=self.get_seleniumwire_options()
        )
        self.add_params()

    def get_options(self):
        options = uc.ChromeOptions()
        options.add_argument(f'--load-extension={PROJECT_DIR}/metamask')
        options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:51.0) '
                             f'Gecko/20100101 Firefox/51.0')
        return options

    def get_seleniumwire_options(self):
        if self.proxy:
            return {'proxy': {'https': self.proxy}}

    def add_params(self):
        self.driver.implicitly_wait(15)


class MetaMaskLoader:

    def __init__(self, driver: WebDriver, private_key: str, address: str):
        self.driver = driver
        self.private_key = private_key
        self.address = address
        self.action = ActionChains(self.driver)

    def connect_wallet(self):
        self.driver.set_page_load_timeout(30)
        try:
            self.driver.get(URL)
        except BaseException:
            print(1)
        logger.info(f'{self.address} || Creating metamask wallet')
        sleep(SLEEP)
        self._create_wallet()
        self._import_account()
        logger.info(f'{self.address} || Created')

    def _create_wallet(self):
        self.driver.switch_to.window(self.driver.window_handles[1])
        sleep(SHORT_SLEEP)
        self.driver.refresh()
        sleep(SHORT_SLEEP)
        self.driver.find_element(By.CLASS_NAME, value='dropdown__select').click()
        self.driver.find_element(By.XPATH, value=f"//option[@value='en']").click()
        sleep(SHORT_SLEEP)
        self.driver.find_element(By.CLASS_NAME, value='check-box').click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Create a new wallet')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'I agree')]").click()
        self._input_wallet_password()
        self.driver.find_element(By.CLASS_NAME, value='check-box').click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Create a new wallet')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Remind me later')]").click()
        self.driver.find_element(By.CLASS_NAME, value='check-box').click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Skip')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Got it!')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Next')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Done')]").click()

    def _input_wallet_password(self):
        pass_inputs = self.driver.find_elements(
            By.CLASS_NAME, value="form-field__input")
        for pass_input in pass_inputs:
            pass_input.send_keys(PASSWORD)

    def _import_account(self):
        self.action.move_by_offset(50, 50).click().perform()
        self.driver.find_element(By.XPATH, value=f"//span[contains(text(),'Account 1')]").click()
        self.driver.find_element(By.XPATH, value=f"//button[contains(text(),'Add account')]").click()
        self.driver.find_element(By.XPATH, value=f"//button[contains(text(),'Import account')]").click()
        key_input =self.driver.find_element(By.CLASS_NAME, value="mm-input")
        key_input.send_keys(self.private_key)
        self.driver.find_elements(By.XPATH, value=f"//button[contains(text(),'Import')]")[1].click()

    def change_network(self):
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Ethereum Mainnet')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Add network')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//*[contains(text(),'Add a network manually')]").click()
        self._input_network_data()
        self.driver.close()
        _wait_and_open_window(self.driver, 0)

    def _input_network_data(self):
        for _ in range(20):
            inputs = self.driver.find_elements(By.CLASS_NAME, value='form-field__input')
            network_data = [
                'Scroll', 'https://rpc.scroll.io', '534352',
                'ETH', 'https://blockscout.scroll.io/']
            for i, data in enumerate(network_data):
                inputs[i].send_keys(data)
            try:
                self.driver.find_element(
                    By.XPATH, value=f"//*[contains(text(),'Save')]").click()
                return
            except BaseException:
                self.driver.refresh()
        raise ValueError("Can't choose network")


class ElementMarketBuyer:

    def __init__(
        self,
        driver: WebDriver,
        private_key: str,
        address: str,
        min_price: float,
        max_price: float,
    ):
        self.driver = driver
        self.private_key = private_key
        self.address = address
        self.min_price = min_price
        self.max_price = max_price
        self.action = ActionChains(self.driver)

    def change_network(self):
        self._connect_wallet()
        self._change_network()
        logger.info(f'{self.address} || Wallet Connected')

    def _change_network(self):
        self.driver.find_element(
            By.XPATH, value=f"//div[contains(text(),'Ethereum')]").click()
        sleep(SHORT_SLEEP)
        self.driver.find_element(
            By.XPATH, value="//div[contains(@class, 'layout-header-popover-item')]"
                            "//div[contains(text(),'Scroll')]").click()
        sleep(SHORT_SLEEP)

    def _connect_wallet(self):
        self.action.move_by_offset(50, 50).click().perform()
        self.driver.find_element(By.CLASS_NAME, value='connect-wallet').click()
        self.driver.find_element(
            By.XPATH, value=f"//span[contains(text(),'MetaMask')]").click()
        sleep(SHORT_SLEEP)
        self.driver.switch_to.window(self.driver.window_handles[1])
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Next')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Connect')]").click()
        self.driver.find_element(
            By.XPATH, value=f"//button[contains(text(),'Cancel')]").click()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def _input_prices(self):
        """
        Спустя рандомное время 5-8 сек открывается окно с подписанием каких-то условий,
        мы кладём close на это окно
        """
        self.driver.find_element(By.XPATH, value=f"//div[contains(text(),'Price')]").click()
        price_inputs = self.driver.find_elements(By.CLASS_NAME, value='filter-price-input')
        price_inputs[0].send_keys(0.00000001)
        price_inputs[1].send_keys(0.00001)
        self.driver.find_element(By.XPATH, value=f"//button[contains(text(),'Apply')]").click()
        sleep(SLEEP)

    def buy(self):
        logger.info(f'{self.address} || Looking for item')
        self._input_prices()
        items = self.driver.find_elements(
            By.CLASS_NAME, value="element-asset-grid-item")
        if len(items) <= 8:
            raise ValueError('Price is inadequate. Items not found')
        items[7].click()
        return self._pay()

    def _pay(self):
        self.driver.find_element(By.CLASS_NAME, value='header-nav-shopping-cart').click()
        price = self.driver.find_element(By.CLASS_NAME, value='cart-asset-price').text
        self.driver.find_element(
            By.XPATH, value="//span[contains(text(),'Pay')]").click()
        sleep(SLEEP * 2)
        logger.info(f'{self.address} || Confirming transaction')
        self.driver.switch_to.window(self.driver.window_handles[1])
        self._sign_transaction()
        return price

    def _sign_transaction(self):
        confirm_btn = self.driver.find_element(
            By.XPATH, value="//button[contains(text(),'Confirm')]")
        if not self.is_button_available(confirm_btn):
            raise ValueError('Confirm button unavailable')
        confirm_btn.click()
        sleep(SLEEP)
        self.driver.switch_to.window(self.driver.window_handles[0])

    @staticmethod
    def is_button_available(btn):
        for _ in range(5):
            sleep(SLEEP)
            if btn.is_enabled():
                return True


def waiting_gas_price(w3: Web3, desired_gas_price: int):
    while True:
        gas_price = w3.eth.gas_price
        if gas_price <= desired_gas_price:
            return
        logger.info(f'Waiting gas price. Now: {gas_price}')
        sleep(GAS_WAITING)


class ElementMarketAgent(IProtocol):

    def __init__(
        self,
        account,
        max_gas_price: int,
        proxy: Proxy,
        size: str,
        *args,
        **kwargs,
    ):
        self.account = account
        self.max_gas_price = max_gas_price
        self.proxy = proxy
        self.size = size

        self._sender = None

    def ready(self) -> bool:
        return True

    def go(self) -> bool:
        logger.info(f'{self.account.address} || Protocol: {self.name}. {self.size}')
        ProxyAgent.reset_proxy()
        driver = ChromeCreator(self.proxy.address).driver
        try:
            price = self.make_action(driver)
            ScrollCombine.create(
                address=self.account.address,
                protocol=self.name,
                srcCurrency='ETH',
                srcAmount=price,
            )
            logger.info(f'{self.account.address} || Purchased NFT for {price} ETH')
            return True
        except BaseException as error:
            logger.error(traceback.format_exc())
            driver.save_screenshot(f'logs/screenshots/{datetime.now()}.png')
            raise error
        finally:
            driver.quit()

    def make_action(self, driver):
        w3 = Web3(Web3.HTTPProvider(MAIN_RPC))
        mm_loader = MetaMaskLoader(
            driver=driver,
            private_key=self.account._private_key.hex(),
            address=self.account.address,
        )
        mm_loader.connect_wallet()
        mm_loader.change_network()
        buyer = ElementMarketBuyer(
            driver=driver,
            private_key=self.account._private_key.hex(),
            address=self.account.address,
            min_price=ELEMENT_MIN_PRICE,
            max_price=ELEMENT_MAX_PRICE,
        )
        buyer.change_network()
        waiting_gas_price(w3, self.max_gas_price)
        return buyer.buy()

    @property
    def name(self):
        return 'ElementMarket'
