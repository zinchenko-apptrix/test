from abc import ABC, abstractmethod

from services.logger import logger


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