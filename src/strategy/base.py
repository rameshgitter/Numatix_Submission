from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, closes_15m, closes_1h):
        pass
    
    @abstractmethod
    def on_trade_entry(self, *args, **kwargs):
        pass
    
    @abstractmethod
    def on_trade_exit(self, *args, **kwargs):
        pass
