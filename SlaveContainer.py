import asyncio
from ExchangeInterfaces.BinanceExchange import BinanceExchange
from ExchangeInterfaces.BitmexExchange import BitmexExchange
from ExchangeInterfaces.Exchange import Exchange


def factory_method_create_exchange(single_config, pairs) -> Exchange:
    exchange_name = single_config['exchange_name']
    necessary_class = globals()[exchange_name]
    necessary_object = necessary_class(single_config['key'], single_config['secret'], pairs)
    return necessary_object


class SlaveContainer:
    def __init__(self, config, pairs):

        self.master = factory_method_create_exchange(config['master'], pairs)

        # single_config = config['master']
        # exchange_name = single_config['exchange_name']
        # necessary_class = globals()[exchange_name]
        # self.master = necessary_class(config['master']['key'], config['master']['secret'], pairs)

        slaves = []
        for slave_config in config['slaves']:
            slave = factory_method_create_exchange(slave_config, pairs)

            # slave = necessary_class(slave_config['key'], slave_config['secret'], pairs)
            slaves.append(slave)
        self.slaves = slaves

    def start(self):
        self.master.start(self.on_order_caller)

    def stop(self):
        self.master.stop()
        for slave in self.slaves:
            slave.stop()

    def on_order_caller(self, event):
        # callback for event new order
        print(event)

        p_event = self.master.process_event(event)

        if p_event is None:
            return

        for slave in self.slaves:
            asyncio.run(slave.on_order_handler(p_event))

    def first_copy(self, orders):
        # copy open orders from master account to slaves

        # orders = self.master.get_open_orders()
        for slave in self.slaves:
            for o in orders:
                asyncio.run(slave.async_create_order(o))
