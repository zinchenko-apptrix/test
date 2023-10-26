import os
import requests
from time import sleep
from typing import Optional

from services.logger import logger
from database.other.models import Proxy


class ProxyAgent:

    def __init__(self, retries: int, retry_delay: int):
        self.retries = retries
        self.retry_delay = retry_delay
        self.failed_customers = []

    def rotate(self, address: str) -> Proxy:
        proxy = self.get_proxy(address)
        if proxy:
            logger.info(f'{address} || proxy: {proxy.address}')
            return proxy
        self.reset_proxy()
        logger.error(f'{address} || Proxy not found')

    def get_proxy(self, address: str) -> Proxy:
        proxies = Proxy.get_proxy(address=address)
        for proxy in proxies:
            if self.check_proxy(proxy):
                proxy.update_success_proxy(address)
                return proxy
        else:
            self.failed_customers.append(address)

    def check_proxy(self, proxy: Proxy) -> Optional[bool]:
        os.environ['HTTPS_PROXY'] = proxy.address
        os.environ['HTTP_PROXY'] = proxy.address
        for _ in range(self.retries + 1):
            if self.request(proxy):
                return True
            sleep(self.retry_delay)
        else:
            logger.error(f'Proxy is not alive: {proxy.address}')
            proxy.update_last_using()

    @staticmethod
    def request(proxy, timeout: int = 5):
        try:
            requests.get('https://google.com', timeout=timeout)
            return True
        except BaseException as err:
            logger.error(f'Proxy error {proxy.address}: {err}')

    @staticmethod
    def reset_proxy():
        os.environ['HTTPS_PROXY'] = ''
        os.environ['HTTP_PROXY'] = ''

    @property
    def list_fails(self):
        return "\n" + "\n".join(self.failed_customers)