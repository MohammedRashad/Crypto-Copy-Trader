from abc import ABC, abstractmethod


class Exchange(ABC):
    balance = None
    exchange_name = None
    master_balance = None

    def __init__(self, apiKey, apiSecret, pairs, ):
        self.api = {'key': apiKey,
                    'secret': apiSecret}
        # delete '\n' from symbols'
        self.pairs = list(map(lambda pair: pair.replace('\n', ''), pairs))

    def get_balance(self):
        return self.balance

    def get_trading_symbols(self):
        symbols = set()
        for pair in self.pairs:
            pair = str(pair)
            symbols.add(pair[:3])
            symbols.add(pair[3:])
        return symbols

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def start(self, caller_callback):
        pass

    @abstractmethod
    def process_event(self, event):
        pass

    @abstractmethod
    def on_order_handler(self, event):
        pass

    @abstractmethod
    def get_open_orders(self):
        pass

    @abstractmethod
    async def on_cancel_handler(self, event):
        pass

    @abstractmethod
    def create_order(self, order):
        pass

    async def async_create_order(self, order):
        self.create_order(order)

    @abstractmethod
    def get_part(self, symbol, quantity, price):
        pass

    @abstractmethod
    def calc_quantity_from_part(self, symbol, quantityPart, price, side):
        pass
