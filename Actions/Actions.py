import inspect
from abc import ABC


class Action(ABC):
    name = 'abstract_action'

    def __init__(self, exchange, original_event):
        self.exchange = exchange
        self.original_event = original_event

    def __str__(self):
        # print all attributes
        attributes = {}
        for i in inspect.getmembers(self):
            # Ignores anything starting with underscore
            # (that is, private and protected attributes)
            if not i[0].startswith('_'):
                # Ignores methods
                if not inspect.ismethod(i[1]) and not i[0] == 'original_event':
                    attributes[i[0]] = i[1]
        return str(attributes)


class ActionNewOrder(Action):
    name = 'new_order'

    def __init__(self, order, exchange, original_event):
        super().__init__(exchange, original_event)
        self.order = order


class ActionCancel(Action):
    name = 'cancel'

    def __init__(self, symbol, price, order_id, exchange, original_event):
        super().__init__(exchange, original_event)
        self.symbol = symbol
        self.price = price
        self.order_id = order_id


class ActionClosePosition(Action):
    name = 'close_position'

    def __init__(self, symbol, order_type, price, order_id, exchange, original_event):
        super().__init__(exchange, original_event)
        self.symbol = symbol
        self.price = price
        self.order_id = order_id
        self.order_type = order_type
