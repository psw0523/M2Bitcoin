from abc import ABC, abstractmethod

class Exchange(ABC):
    @abstractmethod
    def get_ticker(self, currency_type=None):
        pass

    @abstractmethod
    def get_orderbook(self, currency_type=None, count=10):
        pass

    @abstractmethod
    def get_recent(self, currency_type=None, count=10):
        pass

    @abstractmethod
    def get_fee(self):
        pass

    @abstractmethod
    def get_states(self, currency):
        pass
