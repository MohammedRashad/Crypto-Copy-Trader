import math
import Actions.Actions as Actions

from binance.exceptions import BinanceAPIException

from .Exchange import Exchange
from binance.client import Client
from binance.websockets import BinanceSocketManager
from Helpers.Order import Order


class BinanceExchange(Exchange):
    exchange_name = "Binance"
    isMargin = False

    def __init__(self, apiKey, apiSecret, pairs, name):
        super().__init__(apiKey, apiSecret, pairs, name)

        self.connection = Client(self.api['key'], self.api['secret'])

        symbol_info_arr = self.connection.get_exchange_info()
        dict_symbols_info = {item['symbol']: item for item in symbol_info_arr["symbols"]}
        actual_symbols_info = {symbol: dict_symbols_info[symbol] for symbol in self.pairs}
        self.symbols_info = actual_symbols_info

        self.update_balance()
        self.socket = BinanceSocketManager(self.connection)
        self.socket.start_user_socket(self.on_balance_update)
        self.socket.start()
        self.is_last_order_event_completed = True
        self.step_sizes = {}
        self.balance_updated = True

        for symbol_info in symbol_info_arr['symbols']:
            if symbol_info['symbol'] in self.pairs:
                self.step_sizes[symbol_info['symbol']] = \
                    [f['stepSize'] for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'][0]

    def start(self, caller_callback):
        self.socket.start_user_socket(caller_callback)

    def update_balance(self):
        account_information = self.connection.get_account()
        self.set_balance(account_information['balances'])

    def get_trading_symbols(self):
        symbols = set()
        if not self.symbols_info:
            raise RuntimeError("Cant get exchange info")
        for key, value in self.symbols_info.items():
            symbols.add(value["quoteAsset"])
            symbols.add(value["baseAsset"])
        return symbols

    def set_balance(self, balances):
        symbols = self.get_trading_symbols()
        dict_balances = {item['asset']: item for item in balances}
        actual_balance = {symbol: dict_balances[symbol] for symbol in symbols}
        self.balance = actual_balance

    def on_balance_update(self, upd_balance_ev):
        if upd_balance_ev['e'] == 'outboundAccountPosition':
            balance = []
            for ev in upd_balance_ev['B']:
                balance.append({'asset': ev['a'],
                                'free': ev['f'],
                                'locked': ev['l']})
            self.balance.update({item['asset']: item for item in balance})

    def get_open_orders(self):
        orders = self.connection.get_open_orders()
        general_orders = []
        for o in orders:
            quantityPart = self.get_part(o['symbol'], o["origQty"], o['price'], o['side'])
            general_orders.append(
                Order(o['price'], o["origQty"], quantityPart, o['orderId'], o['symbol'], o['side'], o['type'],
                      self.exchange_name))
        return general_orders

    def _cancel_order(self, order_id, symbol):
        self.connection.cancel_order(symbol=symbol, orderId=order_id)
        self.logger.info(f'{self.name}: Order canceled')

    async def on_cancel_handler(self, event: Actions.ActionCancel):
        try:
            slave_order_id = self._cancel_order_detector(event.price)
            self._cancel_order(slave_order_id, event.symbol)
        except BinanceAPIException as error:
            self.logger.error(f'{self.name}: error {error.message}')
        except:
            self.logger.error(f"{self.name}: error in action: {event.name} in slave {self.name}")

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

        # if this event in general type it was send from start function and need call firs_copy
        if 'exchange' in event:
            return event

        if event['e'] == 'outboundAccountPosition':
            self.on_balance_update(event)

        elif event['e'] == 'executionReport':
            if event['X'] == 'FILLED':
                return
            elif event['x'] == 'CANCELED':
                return Actions.ActionCancel(
                    event['s'],
                    event['p'],
                    event['i'],
                    self.exchange_name,
                    event
                )
            elif event['X'] == 'NEW':
                order_event = event

                if order_event['s'] not in self.pairs:
                    return

                if order_event['o'] == 'MARKET':  # if market order, we haven't price and cant calculate quantity
                    order_event['p'] = self.connection.get_ticker(symbol=order_event['s'])['lastPrice']

                # part = self.get_part(order_event['s'], order_event['q'], order_event['p'], order_event['S'])

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
                return Actions.ActionNewOrder(order,
                                              self.exchange_name,
                                              event)
            return

    async def on_order_handler(self, event: Actions.ActionNewOrder):
        self.create_order(event.order)

    def create_order(self, order):
        """
        :param order:
        """
        quantity = self.calc_quantity_from_part(order.symbol, order.quantityPart, order.price, order.side)
        self.logger.info('Slave ' + self.name + ' ' + str(self._get_quote_balance(order.symbol)) + ' '
                         + str(self._get_base_balance(order.symbol)) +
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
            if order.type == 'MARKET':
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
            self.logger.info(f"{self.name}: order created")
        except Exception as e:
            self.logger.error(str(e))

    def _get_quote_balance(self, symbol):
        return self.balance[self.symbols_info[symbol]['quoteAsset']]

    def _get_base_balance(self, symbol):
        return self.balance[self.symbols_info[symbol]['baseAsset']]

    def get_part(self, symbol: str, quantity: float, price: float, side: str):
        # get part of the total balance of this coin

        # if order[side] == sell: need obtain coin balance
        if side == 'BUY':
            get_context_balance = self._get_quote_balance
            market_value = float(quantity) * float(price)
        else:
            get_context_balance = self._get_base_balance
            market_value = float(quantity)

        balance = float(get_context_balance(symbol)['free'])

        # if first_copy the balance was update before
        if self.balance_updated:
            balance += float(get_context_balance(symbol)['locked'])
        # else:
        #     balance += market_value

        part = market_value / balance
        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, side):
        # calculate quantity from quantityPart

        # if order[side] == sell: need obtain coin balance

        if side == 'BUY':
            get_context_balance = self._get_quote_balance
            buy_koef = float(price)
        else:
            get_context_balance = self._get_base_balance
            buy_koef = 1

        cur_bal = float(get_context_balance(symbol)['free'])

        if self.balance_updated:
            cur_bal += float(get_context_balance(symbol)['locked'])

        quantity = quantityPart * cur_bal / buy_koef

        stepSize = float(self.step_sizes[symbol])
        precision = int(round(-math.log(stepSize, 10), 0))
        quantity = round(quantity, precision)
        return quantity
