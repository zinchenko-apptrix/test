import traceback
from datetime import datetime
from time import sleep

from web3 import Web3
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from database.models import ScrollCombine
from database.other.models import Proxy
from protocols.base import IProtocol
from protocols.metamask import ChromeCreator, MetaMaskLoader, is_button_available
from services.logger import logger
from services.proxy import ProxyAgent
from settings.config import (
    GAS_WAITING,
    SHORT_SLEEP,
    SLEEP,
    MAIN_RPC, ELEMENT_MIN_PRICE, ELEMENT_MAX_PRICE,
)


URL = 'https://element.market/assets'


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
        if not is_button_available(confirm_btn):
            raise ValueError('Confirm button unavailable')
        confirm_btn.click()
        sleep(SLEEP)
        self.driver.switch_to.window(self.driver.window_handles[0])

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
