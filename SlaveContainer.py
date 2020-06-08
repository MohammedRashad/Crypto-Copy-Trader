import asyncio


class SlaveContainer:
    def __init__(self, master, slaves):
        self.is_last_order_event_completed = True
        self.master = master
        self.slaves = slaves

    def start(self):
        self.master.socket.start_user_socket(self.on_order_caller)

    def stop(self):
        self.master.stop()
        for slave in self.slaves:
            slave.stop()

    def on_order_caller(self, event):
        # callback for event new order
        print(event)

        if event['e'] == 'outboundAccountPosition':
            self.is_last_order_event_completed = True

        if event['e'] == 'executionReport':
            if event['X'] == 'FILLED':
                return
            self.last_order_event = event  # store event order_event coz we need in outboundAccountInfo event
            # sometimes can came event executionReport x == filled and x == new together so we need flag
            self.is_last_order_event_completed = False
            return
        elif event['e'] == 'outboundAccountInfo':
            if self.is_last_order_event_completed:
                return

            order_event = self.last_order_event

            if order_event['s'] not in self.master.pairs:
                return

            if order_event['o'] == 'MARKET':  # if market order, we haven't price and cant calculate quantity
                order_event['p'] = self.master.connection.get_ticker(symbol=event['s'])['lastPrice']

            part = self.master.get_part(order_event['s'], order_event['q'], order_event['p'], order_event['S'])

            self.master.on_balance_update(event)
            order_event['q'] = part
            for slave in self.slaves:
                asyncio.run(slave.on_order_handler(order_event))
