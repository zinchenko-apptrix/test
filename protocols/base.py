import json
from abc import ABC, abstractmethod


class IProtocol(ABC):

    @abstractmethod
    def __init__(self, *args, **kwargs):
        ...

    def ready(self) -> bool:
        ...

    def go(self) -> bool:
        ...


    @abstractmethod
    def name(self):
        ...


class ContractMixin:
    def _get_contract(self):
        with open(self.ABI) as file:
            return self.w3.eth.contract(
                address=self.CONTRACT, abi=json.load(file)
            )
