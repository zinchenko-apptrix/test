from dataclasses import dataclass
from time import sleep

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from seleniumwire.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException
import seleniumwire.undetected_chromedriver.v2 as uc

from services.logger import logger
from settings.config import (
    PROJECT_DIR,
    SHORT_SLEEP,
    PASSWORD,
    SLEEP, LONG_SLEEP,
)


def _wait_and_open_window(driver, number_window: int):
    for _ in range(20):
        if len(driver.window_handles) >= number_window + 1:
            driver.switch_to.window(driver.window_handles[number_window])
            return
        sleep(SHORT_SLEEP)
    raise ValueError(f'Window not opening. Slow internet connection / Bad Proxy')


def is_button_available(btn):
    for _ in range(20):
        sleep(SHORT_SLEEP)
        if btn.is_enabled():
            return True


class DriverCreator:

    def add_params(self):
        self.driver.implicitly_wait(15)

    def get_seleniumwire_options(self):
        if self.proxy:
            return {'proxy': {'https': self.proxy}}


class ChromeCreator(DriverCreator):

    def __init__(self, proxy=None):
        self.proxy = proxy
        self.driver = uc.Chrome(
            options=self.get_options(),
            seleniumwire_options=self.get_seleniumwire_options()
        )
        self.add_params()

    def get_options(self):
        options = uc.ChromeOptions()
        options.add_argument(f'--load-extension={PROJECT_DIR}/metamask/chrome')
        options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:51.0) '
                             f'Gecko/20100101 Firefox/51.0')
        return options


class FireFoxCreator(DriverCreator):

    def __init__(self, proxy=None, extension=f'{PROJECT_DIR}/metamask/firefox.xpi'):
        self.proxy = proxy
        self.extenxion = extension
        self.driver = Firefox(
            options=self.get_options(),
            seleniumwire_options=self.get_seleniumwire_options()
        )
        self.driver.install_addon(self.extenxion, temporary=True)
        self.add_params()

    def get_options(self):
        options = Options()
        # options.add_argument('--headless')
        return options


@dataclass
class Network:
    name: str
    rpc: str
    chain_id: int
    currency: str
    explorer: str

    def list(self):
        return [self.name, self.rpc, self.chain_id, self.currency, self.explorer]


class MetaMaskLoader:

    def __init__(
        self,
        driver: WebDriver,
        private_key: str,
        address: str,
        network: Network,
    ):
        self.driver = driver
        self.private_key = private_key
        self.address = address
        self.network = network
        self.action = ActionChains(self.driver)

    def connect_wallet(self):
        logger.info(f'{self.address} || Creating metamask wallet')
        sleep(SLEEP)
        self._create_wallet()
        self._import_account()

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
        if self.driver.__class__ == uc.Chrome:
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
            for i, data in enumerate(self.network.__dict__.values()):
                inputs[i].send_keys(data)
            try:
                self.driver.find_element(
                    By.XPATH, value=f"//*[contains(text(),'Save')]").click()
                return
            except BaseException:
                self.driver.refresh()
        raise ValueError("Can't choose network")
