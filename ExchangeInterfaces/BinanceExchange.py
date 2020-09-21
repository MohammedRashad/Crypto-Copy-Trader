import math

from binance.exceptions import BinanceAPIException

from .Exchange import Exchange
from binance.client import Client
from binance.websockets import BinanceSocketManager
from Helpers import Order


class BinanceExchange(Exchange):
    exchange_name = "Binance"
    isMargin = False

    def __init__(self, apiKey, apiSecret, pairs, name):
        super().__init__(apiKey, apiSecret, pairs, name=name)

        self.connection = Client(self.api['key'], self.api['secret'])
        self.update_balance()
        self.socket = BinanceSocketManager(self.connection)
        self.socket.start_user_socket(self.on_balance_update)
        self.socket.start()
        self.is_last_order_event_completed = True
        self.step_sizes = {}
        self.balance_updated = True
        symbol_info_arr = self.connection.get_exchange_info()
        for symbol_info in symbol_info_arr['symbols']:
            if symbol_info['symbol'] in self.pairs:
                self.step_sizes[symbol_info['symbol']] = \
                    [f['stepSize'] for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'][0]

    def start(self, caller_callback):
        self.socket.start_user_socket(caller_callback)

    def update_balance(self):
        account_information = self.connection.get_account()
        self.set_balance(account_information['balances'])

    def set_balance(self, balances):
        symbols = self.get_trading_symbols()
        actual_balance = list(filter(lambda elem: str(elem['asset']) in symbols, balances))
        self.balance = actual_balance

    def on_balance_update(self, upd_balance_ev):
        if upd_balance_ev['e'] == 'outboundAccountInfo':
            balance = []
            for ev in upd_balance_ev['B']:
                balance.append({'asset': ev['a'],
                                'free': ev['f'],
                                'locked': ev['l']})
            self.set_balance(balance)

    def get_open_orders(self):
        orders = self.connection.get_open_orders()
        general_orders = []
        for o in orders:
            quantityPart = self.get_part(o['symbol'], o["origQty"], o['price'], o['side'])
            general_orders.append(
                Order(o['price'], o["origQty"], quantityPart, o['orderId'], o['symbol'], o['side'], o['type'],
                      self.exchange_name))
        return general_orders

    def _cancel_order(self, orderId, symbol):
        self.connection.cancel_order(symbol=symbol, orderId=orderId)
        print('order canceled')

    async def on_cancel_handler(self, event):
        try:
            slave_order_id = self._cancel_order_detector(event['price'])
            self._cancel_order(slave_order_id, event['symbol'])
        except BinanceAPIException as error:
            print(f'{self.name} error {error.message}')
        except:
            print(f"error in action: {event['action']} in slave {self.name}")

    def stop(self):
        self.socket.close()

    def _cancel_order_detector(self, price):
        # detect order id which need to be canceled
        slave_open_orders = self.connection.get_open_orders()
        for ordr_open in slave_open_orders:
            if float(ordr_open['price']) == float(price):
                return ordr_open['orderId']

    def process_event(self, event):
        # return event in generic type from websocket

        if event['e'] == 'outboundAccountPosition':
            self.is_last_order_event_completed = True

        if event['e'] == 'executionReport':
            if event['X'] == 'FILLED':
                return
            elif event['x'] == 'CANCELED':
                return {'action': 'cancel',
                        'symbol': event['s'],
                        'price': event['p'],
                        'exchange': self.exchange_name,
                        'original_event': event
                        }
            self.last_order_event = event  # store event order_event coz we need in outboundAccountInfo event
            # sometimes can came event executionReport x == filled and x == new together so we need flag
            self.is_last_order_event_completed = False
            return

        elif event['e'] == 'outboundAccountInfo':
            if self.is_last_order_event_completed:
                return

            order_event = self.last_order_event

            if order_event['s'] not in self.pairs:
                return

            if order_event['o'] == 'MARKET':  # if market order, we haven't price and cant calculate quantity
                order_event['p'] = self.connection.get_ticker(symbol=order_event['s'])['lastPrice']

            # part = self.get_part(order_event['s'], order_event['q'], order_event['p'], order_event['S'])

            self.on_balance_update(event)

            # shortcut mean https://github.com/binance-exchange/binance-official-api-docs/blob/master/user-data-stream.md#order-update
            order = Order(order_event['p'],
                          order_event['q'],
                          self.get_part(order_event['s'], order_event['q'], order_event['p'], order_event['S']),
                          order_event['i'],
                          order_event['s'],
                          order_event['S'],
                          order_event['o'],
                          self.exchange_name,
                          order_event['P'])
            return {
                'action': 'new_order',
                'order': order,
                'exchange': self.exchange_name,
                'original_event': event
            }

    async def on_order_handler(self, event):
        self.create_order(event['order'])

    def create_order(self, order):
        """
        :param order:
        """
        quantity = self.calc_quantity_from_part(order.symbol, order.quantityPart, order.price, order.side)
        print('Slave ' + self.name + str(self._get_balance_market_by_symbol(order.symbol)) + ' '
              + str(self._get_balance_coin_by_symbol(order.symbol)) +
              ', Create Order:' + ' amount: ' + str(quantity) + ', price: ' + str(order.price))
        try:
            if order.type == 'STOP_LOSS_LIMIT' or order.type == "TAKE_PROFIT_LIMIT":
                self.connection.create_order(symbol=order.symbol,
                                             side=order.side,
                                             type=order.type,
                                             price=order.price,
                                             quantity=quantity,
                                             timeInForce='GTC',
                                             stopPrice=order.stop)
            elif order.type == 'MARKET':
                self.connection.create_order(symbol=order.symbol,
                                             side=order.side,
                                             type=order.type,
                                             quantity=quantity)
            else:
                self.connection.create_order(symbol=order.symbol,
                                             side=order.side,
                                             type=order.type,
                                             quantity=quantity,
                                             price=order.price,
                                             timeInForce='GTC')
            print("order created")
        except Exception as e:
            print(str(e))

    def _get_balance_market_by_symbol(self, symbol):
        return list(filter(lambda el: el['asset'] == symbol[3:], self.get_balance()))[0]

    def _get_balance_coin_by_symbol(self, symbol):
        return list(filter(lambda el: el['asset'] == symbol[:3], self.get_balance()))[0]

    def get_part(self, symbol, quantity, price, side):
        # get part of the total balance of this coin

        # if order[side] == sell: need obtain coin balance
        if side == 'BUY':
            get_context_balance = self._get_balance_market_by_symbol
            market_value = float(quantity) * float(price)
        else:
            get_context_balance = self._get_balance_coin_by_symbol
            market_value = float(quantity)

        balance = float(get_context_balance(symbol)['free'])

        # if first_copy the balance was update before
        if self.balance_updated:
            balance += float(get_context_balance(symbol)['locked'])
        else:
            balance += market_value

        part = market_value / balance

        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, side):
        # calculate quantity from quantityPart

        # if order[side] == sell: need obtain coin balance

        if side == 'BUY':
            get_context_balance = self._get_balance_market_by_symbol
            buy_koef = float(price)
        else:
            get_context_balance = self._get_balance_coin_by_symbol
            buy_koef = 1

        cur_bal = float(get_context_balance(symbol)['free'])

        if self.balance_updated:
            cur_bal += float(get_context_balance(symbol)['locked'])

        quantity = quantityPart * cur_bal / buy_koef

        stepSize = float(self.step_sizes[symbol])
        precision = int(round(-math.log(stepSize, 10), 0))
        quantity = round(quantity, precision)
        return quantity
