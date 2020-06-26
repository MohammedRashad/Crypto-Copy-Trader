import asyncio
from ExchangeInterfaces.BinanceExchange import BinanceExchange


def ex_name_to_class(single_config):
    exchange_name = single_config['exchange_name']
    necessary_class = globals()[exchange_name]
    return necessary_class


class SlaveContainer:
    def __init__(self, config, pairs):

        # necessary_class = ex_name_to_class(config['master'])
        single_config = config['master']
        exchange_name = single_config['exchange_name']
        necessary_class = globals()[exchange_name]
        self.master = necessary_class(config['master']['key'], config['master']['secret'], pairs)

        slaves = []
        for slave_config in config['slaves']:
            # necessary_class = ex_name_to_class(slave_config)

            exchange_name = slave_config['exchange_name']
            necessary_class = globals()[exchange_name]

            slave = necessary_class(slave_config['key'], slave_config['secret'], pairs)
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

    def first_copy(self):
        orders = self.master.get_open_orders()
        for slave in self.slaves:
            for o in orders:
                asyncio.run(slave.create_order(o['']))
        
