import threading

from .Exchange import Exchange
from bitmex_websocket import BitMEXWebsocket
from websocket import create_connection
import bitmex
import json
import platform
import os
from Helpers import Order

BITMEX_URL = "wss://testnet.bitmex.com"
# BITMEX_URL = "wss://www.bitmex.com"

ENDPOINT = "/realtime"


class BitmexExchange(Exchange):
    exchange_name = "Bitmex"
    isMargin = True

    def __init__(self, apiKey, apiSecret, pairs, name):


        super().__init__(apiKey, apiSecret, pairs, name)
        self.pairs = list(map(lambda pair: self.translate(pair) if  pair != self.translate(pair)
                                        else print(f"Can't translate word {pair} in {BitmexExchange.exchange_name}"), self.pairs))
        self.pairs = list(filter(None, self.pairs))
        self.connection = bitmex.bitmex(api_key=apiKey, api_secret=apiSecret)
        self.socket = {}
        for pair in self.pairs:
            self.socket[pair] = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair,
                                               api_key=self.api['key'],
                                               api_secret=self.api['secret'], on_balance_update=self.on_balance_update)


    def start(self, caller_callback):
        self.stop()
        for pair in self.pairs:
                self.socket[pair] = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair,
                                      api_key=self.api['key'],
                                      api_secret=self.api['secret'], on_order_calback=caller_callback,
                                      on_balance_update=self.on_balance_update)

    def stop(self):
        for pair in self.pairs:
            self.socket[pair].exit()

    def on_balance_update(self, event):
        if 'availableMargin' in event:
            self.balance = event['availableMargin']
            print(f"{self.name} Balance Updated: {event['availableMargin']}")

    def update_balance(self):
        self.balance = self.socket[self.pairs[0]].funds()['availableMargin']

        # using rest api
        # response = self.connection.User.User_getMargin().result()
        # self.balance = response[0]['availableMargin']

    def get_open_orders(self):
        open_orders = []
        if not self.socket:
            open_orders = self.connection.Order.Order_getOrders(filter=str("{\"open\": \"true\"}")).result()[0]
        else:
            for pair in self.pairs:
                open_orders += self.socket[pair].open_orders(clOrdIDPrefix="")

        # open_orders = list(filter(lambda o: o['ordStatus'] == 'New', orders[0]))
        general_orders = []
        for o in open_orders:
            general_orders.append(self._self_order_to_global(o))
        return general_orders

    def get_part(self, symbol, quantity, price):
        btc = float(quantity) / float(price)
        btc_satoshi = btc * (10 ** 8)
        part = float(btc_satoshi) / float(self.get_balance())
        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, **kwargs):
        btc_satoshi = float(quantityPart) * float(self.get_balance())
        btc = btc_satoshi / (10 ** 8)
        amount_usd = float(btc) * float(price)
        return amount_usd

    def process_event(self, event):
        self.update_balance()

        if event['action'] == "insert":

            check_result = self.check_expected_order(event)
            if check_result:
                return check_result

            if event['data'][0]['ordStatus'] == 'New':
                if event['data'][0]['side'] == '':

                    close_order = event['data'][0]
                    # order to close position came
                    if close_order['ordType'] == 'Market':
                        # positions = self.connection.Position.Position_get(filter=str("{\"symbol\": \""
                        # close_order['orderQty'] = self.get_balance()
                        return {'action': 'close_position',
                                'symbol': self.translate(close_order['symbol']),
                                'type': self.translate(close_order['ordType']),
                                'price': None,
                                'id': close_order['orderID'],
                                'exchange': self.exchange_name,
                                'original_event': event
                                }
                    elif close_order['ordType'] == 'Limit':
                        # self.add_expected_order_id(close_order['orderID'], self._master_close_limit_order)
                        return {'action': 'close_position',
                                'symbol': self.translate(close_order['symbol']),
                                'type': self.translate(close_order['ordType']),
                                'price': close_order['price'],
                                'id': close_order['orderID'],
                                'exchange': self.exchange_name,
                                'original_event': event
                                }

                # elif event['data'][0]['ordType'] == 'Market' or event['data'][0]['ordType'] == 'Stop':
                #     event['data'][0]['price'] = self.socket.get_instrument()['midPrice']
                order = self._self_order_to_global(event['data'][0])

                return {
                    'action': 'new_order',
                    'order': order,
                    'exchange': self.exchange_name,
                    'original_event': event
                }
        elif event['action'] == 'update':
            if 'ordStatus' not in event['data'][0]:
                return
            if event['data'][0]['ordStatus'] == 'Canceled':
                orders = open_orders = self.connection.Order.Order_getOrders(reverse=True, count=100).result()[0]
                order = list(filter(lambda o: o['orderID'] == event['data'][0]['orderID'],
                                    orders))[0]
                global_order = self._self_order_to_global(order)
                return {'action': 'cancel',
                        'symbol': global_order.symbol,
                        'id': global_order.id,
                        'price': global_order.price,
                        'exchange': self.exchange_name,
                        'original_event': event
                        }
        elif event['action'] == 'partial':
            # # change balance by manually because on_balance_update working after order event came
            balance = self.connection.User.User_getMargin().result()[0]
            self.balance = balance['availableMargin'] + balance['initMargin']
            return {'action': 'first_copy',
                    'exchange': self.exchange_name,
                    'original_event': event
                    }

    async def on_order_handler(self, event):
        self.create_order(event['order'])

    async def on_cancel_handler(self, event):
        if self.is_program_order(event['id']):
            order_id = None
            clOrderId = event['id']
        else:
            order_id = self._cancel_order_detector(event['price'])
            clOrderId = None

        if order_id or clOrderId:
            self._cancel_order(order_id, clOrderId)
        else:
            print(f'Cancel rejected: Cant find necessary order in slave {self.exchange_name}')

    def _self_order_to_global(self, o) -> Order:
        if 'stopPx' not in o:
            o['stopPx'] = 0
        if o['price'] is None:
            o['price'] = self.socket[o['symbol']].get_instrument()['midPrice']
        return Order(o['price'], o["orderQty"],
                     self.get_part(o['symbol'], o["orderQty"], self.socket['XBTUSD'].get_instrument()['midPrice']),
                     o['orderID'],
                     self.translate(o['symbol']),
                     o['side'].upper(),
                     self.translate(o['ordType']),
                     self.exchange_name,
                     stop=o['stopPx'])

    def _cancel_order_detector(self, price):
        # detect order id which need to be canceled
        open_orders = self.get_open_orders()
        for ordr_open in open_orders:
            if ordr_open.price == price:
                return ordr_open.id

    def _cancel_order(self, order_id, clOrderID=None):
        if clOrderID:
            result = self.connection.Order.Order_cancel(clOrdID=clOrderID).result()
        else:
            result = self.connection.Order.Order_cancel(orderID=order_id).result()
        print(result)

    def create_order(self, order):
        if self.translate(order.symbol) == 'XBTUSD':
            quantity = self.calc_quantity_from_part(order.symbol, order.quantityPart, order.price)
        else:
            quantity = self.calc_quantity_from_part(order.symbol, order.quantityPart,
                                                    self.socket['XBTUSD'].get_instrument()['midPrice'])

        print(f"Slave {self.exchange_name}, balance: {self.get_balance()}; "
              f"Create Order: amount {quantity}, price: {order.price}  ")
        self.ids.append(order.id)
        if order.type == 'MARKET' or order.type == 'Stop' or order.type == 'MarketIfTouched':
            new_order = self.connection.Order.Order_new(symbol=self.translate(order.symbol),
                                                        side=self.translate(order.side),
                                                        orderQty=quantity,
                                                        stopPx=order.stop,
                                                        ordType=self.translate(order.type),
                                                        clOrdID=order.id,
                                                        timeInForce='GoodTillCancel')
        else:
            new_order = self.connection.Order.Order_new(symbol=self.translate(order.symbol),
                                                        side=self.translate(order.side),
                                                        orderQty=quantity,
                                                        price=order.price,
                                                        stopPx=order.stop,
                                                        clOrdID=order.id,
                                                        ordType=self.translate(order.type),
                                                        timeInForce='GoodTillCancel'
                                                        )
        print(f'order created: {new_order.result()} ')

    async def close_position(self, event):
        print(f'close_position {event["symbol"]}')

        if event['type'] == 'MARKET':
            return self.connection.Order.Order_new(symbol=self.translate(event["symbol"]), ordType='Market',
                                                   execInst='Close').result()
        else:
            self.ids.append(event['id'])
            return self.connection.Order.Order_new(symbol=self.translate(event["symbol"]), ordType='Limit',
                                                   price=event['price'],
                                                   execInst='Close',
                                                   clOrdID=event['id']).result()

    translate_dict = {
        'BTCUSDT': 'XBTUSD',
        'ETHUSDT': 'ETHUSD',
        'LIMIT': 'Limit',
        'STOP_LOSS_LIMIT': 'StopLimit',
        'MARKET': 'Market',
        'BUY': 'Buy',
        'SELL': 'Sell'
        # 'BCHUSDT': 'BCHUSD',
        # 'TRXUSDT': 'TRXU20',
        # 'XRPUSDT': 'XRPUSD'
    }

    @staticmethod
    def translate(word) -> str:
        translate_dict = BitmexExchange.translate_dict
        if not word in translate_dict:
            translate_dict = dict(zip(BitmexExchange.translate_dict.values(), BitmexExchange.translate_dict.keys()))
            if not word in translate_dict:
                return word
        return translate_dict[word]
