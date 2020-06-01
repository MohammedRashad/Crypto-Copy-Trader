import asyncio

class SlaveContainer:
    def __init__(self, master, slaves):
        self.master = master
        self.slaves = slaves

    def start(self):
        self.master.socket.start_user_socket(self.on_order_caller)

    def on_order_caller(self, event):
        # callback for event new order
        print(event)

        if event['e'] == 'executionReport':
            if event['X'] == 'FILLED':
                return
            self.last_order_event = event # store event order_event coz we need
            return
        elif event['e'] == 'outboundAccountInfo':
            order_event = self.last_order_event

            if order_event['s'] not in self.master.pairs:
                return

            if order_event['o'] == 'MARKET':  # if market order, we haven't price and cant calculate quantity
                order_event['p'] = self.master.connection.get_ticker(symbol=event['s'])['lastPrice']

            part = self.master.get_part(order_event['s'], order_event['q'], order_event['p'])
            self.master.on_balance_update(event)
            order_event['q'] = part
            for slave in self.slaves:
                asyncio.run(slave.on_order_handler(order_event))
