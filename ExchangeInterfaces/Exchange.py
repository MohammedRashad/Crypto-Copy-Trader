from abc import ABC, abstractmethod
import logging
import Actions.Actions as Actions

class Exchange(ABC):
    exchange_name = None
    isMargin = None

    def __init__(self, apiKey, apiSecret, pairs, name):
        self.api = {'key': apiKey,
                    'secret': apiSecret}
        # delete '\n' from symbols'
        self.pairs = list(map(lambda pair: pair.replace('\n', ''), pairs))
        self.name = name
        self.balance = None
        self.expected_orders = list()
        self.ids = []  # store here order which was created by program
        self.logger = logging.getLogger('cct')

    def get_balance(self) -> float:
        return self.balance



    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def start(self, caller_callback):
        pass

    @abstractmethod
    def process_event(self, event) -> Actions.Action or None:
        pass

    @abstractmethod
    def on_order_handler(self, event: Actions.ActionNewOrder):
        pass

    @abstractmethod
    def get_open_orders(self):
        pass

    @abstractmethod
    async def on_cancel_handler(self, event: Actions.ActionCancel):
        pass

    @abstractmethod
    def create_order(self, order):
        pass

    async def async_create_order(self, order):
        self.create_order(order)

    @abstractmethod
    def get_part(self, symbol: str, quantity: float, price: float) -> float:
        pass

    @abstractmethod
    def calc_quantity_from_part(self, symbol: str, quantityPart: float, price: float, side:str):
        pass

    def add_expected_order_id(self, id, callback):
        self.expected_orders.append({'id': id,
                                     'callback': callback})

    def check_expected_order(self, order):
        for expected_order in self.expected_orders:
            if order.id == expected_order['id']:
                expected_order['callback'](order)

    async def close_position(self, event: Actions.ActionClosePosition):
        print(f" exchange {self.exchange_name} do not support event \' close_position \' ")

    def is_program_order(self, _id) -> bool:
        if _id in self.ids:
            return True
        return False

    def delete_id(self, _id):
        self.ids.remove(_id)
