import asyncio
from ExchangeInterfaces.BinanceExchange import BinanceExchange
from ExchangeInterfaces.BitmexExchange import BitmexExchange
from ExchangeInterfaces.Exchange import Exchange
import logging


def factory_method_create_exchange(single_config, pairs) -> Exchange:
    exchange_name = single_config['exchange_name']
    necessary_class = globals()[exchange_name]
    return necessary_class(single_config['key'], single_config['secret'], pairs, single_config['name'])


class SlaveContainer:
    def __init__(self, config, pairs):

        self.logger = logging.getLogger('cct')

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
        # self.start()

    def start(self):
        self.master.start(self.on_event_handler)
        self.logger.info('Launch complete. Now I can copy orders')

    def stop(self):
        self.master.stop()
        for slave in self.slaves:
            slave.stop()

    def on_event_handler(self, event):
        # callback for event new order
        self.logger.debug(event)

        p_event = self.master.process_event(event)

        if p_event is None:
            # ignore this event
            return

        self.logger.info(f'New action came: {{i: p_event[i] for i in p_event if i != "original_event"}}')

        action = p_event['action']
        if action == "cancel":
            for slave in self.slaves:
                asyncio.run(slave.on_cancel_handler(p_event))
        elif action == "new_order":
            for slave in self.slaves:
                asyncio.run(slave.on_order_handler(p_event))
        elif action == "close_position":
            for slave in self.slaves:
                asyncio.run(slave.close_position(p_event))
        elif action == "first_copy":
            self.first_copy(self.master.get_open_orders())

        # store order_id of master order to relate it with slave order
        if action == "new_order":
            for slave in self.slaves:
                slave.ids.append(p_event['order'].id)

        # delete already not existed order ids to avoid memory leak
        if action == "close_position" or action == "cancel":
            ord_id = p_event['id']
            for slave in self.slaves:
                if slave.is_program_order(ord_id):
                    slave.delete_id(ord_id)

    def first_copy(self, orders):
        # copy open orders from master account to slaves

        for slave in self.slaves:
            for o in orders:
                asyncio.run(slave.async_create_order(o))
