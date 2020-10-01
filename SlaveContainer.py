import asyncio
from ExchangeInterfaces.BinanceExchange import BinanceExchange
from ExchangeInterfaces.BitmexExchange import BitmexExchange
from ExchangeInterfaces.BitmexTest import BitmexTest
from ExchangeInterfaces.Exchange import Exchange
import logging
import Actions.Actions as Actions


def factory_method_create_exchange(single_config, pairs) -> Exchange:
    exchange_name = single_config['exchange_name']
    necessary_class = globals()[exchange_name]
    return necessary_class(single_config['key'], single_config['secret'], pairs, single_config['name'])


class SlaveContainer:
    def __init__(self, config, pairs):

        self.logger = logging.getLogger('cct')
        self.logger.info(f"Connecting to the master: {config['master']['name']}...")
        slaves = []
        try:
            self.master = factory_method_create_exchange(config['master'], pairs)
            self.logger.info("Connecting to the slaves. Its can take time...")

            for slave_config in config['slaves']:
                slave = factory_method_create_exchange(slave_config, pairs)
                if self.master.isMargin == slave.isMargin:
                    slaves.append(slave)
                else:
                    slave.stop()
                    del slave
        except:
            self.logger.exception("Error initialing exchanges")

        self.slaves = slaves

    def start(self):
        self.logger.info("Open masters websocket... ")
        self.master.start(self.on_event_handler)
        self.logger.info('Launch complete. Now I can copy orders!')

    def stop(self):
        self.master.stop()
        for slave in self.slaves:
            slave.stop()

    def on_event_handler(self, event):
        # callback for event new order
        self.logger.debug(f'Event came: {event}')

        try:
            p_event = self.master.process_event(event)
        except:
            self.logger.exception('Error in master.process_event()')

        if p_event is None:
            # ignore this event
            return
        self.logger.info('\n')
        self.logger.info(f'New action came: {p_event}')

        if isinstance(p_event, Actions.ActionCancel):
            for slave in self.slaves:
                asyncio.run(slave.on_cancel_handler(p_event))
        elif isinstance(p_event, Actions.ActionNewOrder):
            for slave in self.slaves:
                asyncio.run(slave.on_order_handler(p_event))
        elif isinstance(p_event, Actions.ActionClosePosition):
            for slave in self.slaves:
                asyncio.run(slave.close_position(p_event))

        # store order_id of master order to relate it with slave order
        if isinstance(p_event, Actions.ActionNewOrder):
            for slave in self.slaves:
                slave.ids.append(p_event.order.id)

        # delete already not existed order ids to avoid memory leak
        elif isinstance(p_event, (Actions.ActionClosePosition, Actions.ActionCancel)):
            ord_id = p_event.order_id
            for slave in self.slaves:
                if slave.is_program_order(ord_id):
                    slave.delete_id(ord_id)

    def first_copy(self, orders):
        # copy open orders from master account to slaves

        for slave in self.slaves:
            for o in orders:
                asyncio.run(slave.async_create_order(o))
            slave.balance_updated = False
        self.master.balance_updated = False
