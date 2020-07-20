import asyncio
from ExchangeInterfaces.BinanceExchange import BinanceExchange
from ExchangeInterfaces.BitmexExchange import BitmexExchange
from ExchangeInterfaces.Exchange import Exchange


def factory_method_create_exchange(single_config, pairs) -> Exchange:
    exchange_name = single_config['exchange_name']
    necessary_class = globals()[exchange_name]
    return necessary_class(single_config['key'], single_config['secret'], pairs)


class SlaveContainer:
    def __init__(self, config, pairs):

        self.master = factory_method_create_exchange(config['master'], pairs)

        slaves = []
        for slave_config in config['slaves']:
            slave = factory_method_create_exchange(slave_config, pairs)
            if self.master.isMargin == slave.isMargin:
                slaves.append(slave)
            else:
                slave.stop()
                del slave
        self.slaves = slaves
        #self.start()

    def start(self):
        self.master.start(self.on_event_handler)
        # def pass_callback(): return None
        # for slave in self.slaves:
        #     slave.start(pass_callback)

    def stop(self):
        self.master.stop()
        for slave in self.slaves:
            slave.stop()

    def on_event_handler(self, event):
        # callback for event new order
        print(event)

        p_event = self.master.process_event(event)

        if p_event is None:
            return

        if p_event['action'] == "cancel":
            for slave in self.slaves:
                asyncio.run(slave.on_cancel_handler(p_event))
        elif p_event['action'] == "new_order":
            for slave in self.slaves:
                asyncio.run(slave.on_order_handler(p_event))
        elif p_event['action'] == "close_position":
            for slave in self.slaves:
                asyncio.run(slave.close_position(p_event))
        elif p_event['action'] == "first_copy":
            self.first_copy(self.master.get_open_orders())

    def first_copy(self, orders):
        # copy open orders from master account to slaves

        # orders = self.master.get_open_orders()
        for slave in self.slaves:
            for o in orders:
                asyncio.run(slave.async_create_order(o))
