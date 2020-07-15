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

    def __init__(self, apiKey, apiSecret, pairs):
        pairs = self._pairs_transform_self(pairs)
        super().__init__(apiKey, apiSecret, pairs)

        self.connection = bitmex.bitmex(api_key=apiKey, api_secret=apiSecret)
        self.update_balance()
        self.socket = None

    def start(self, caller_callback):
        self.socket = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol="XBTUSD",
                                      api_key=self.api['key'],
                                      api_secret=self.api['secret'], on_order_calback=caller_callback)

        # pause system (temp solution)
        if platform.system() == "Windows":
            os.system("pause")
        elif platform.system() == "Linux":
            os.system('read -sn 1 -p "Press any key to continue..."')

    def stop(self):
        pass

    def update_balance(self):
        response = self.connection.User.User_getMargin().result()
        self.balance = response[0]['availableMargin']

    def get_open_orders(self):
        if not self.socket:
            open_orders = self.connection.Order.Order_getOrders(filter=str("{\"open\": \"true\"}")).result()[0]
        else:
            open_orders = self.socket.open_orders()
        # open_orders = list(filter(lambda o: o['ordStatus'] == 'New', orders[0]))
        general_orders = []
        for o in open_orders:
            general_orders.append(self._self_order_to_global(o))
        return general_orders

    def get_part(self, symbol, quantity, price):
        btc = float(quantity) / float(price)
        btc_satoshi = btc * (10 ** 8)
        part = float(btc_satoshi) / (float(self.get_balance()) + float(btc_satoshi))
        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, **kwargs):
        btc_satoshi = float(quantityPart) * float(self.get_balance())
        btc = btc_satoshi / (10 ** 8)
        amount_usd = float(btc) * float(price)
        return amount_usd

    def process_event(self, event):

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
                                'exchange': self.exchange_name,
                                'original_event': event
                                }
                    elif close_order['ordType'] == 'Limit':
                        self.add_expected_order_id(close_order['orderID'],
                                                   lambda _close_order: {'action': 'close_position',
                                                                         'symbol': self.translate(_close_order['symbol']),
                                                                         'type': self.translate(_close_order['ordType']),
                                                                         'exchange': self.exchange_name,
                                                                         'original_event': event})
                        return
                    # positions = self.connection.Position.Position_get(filter=str("{\"symbol\": \""
                    # + event['data'][0]['symbol'] + "\"} ")).result()
                    # quantity = positions['openingQty']
                    # side = positions['']
                elif event['data'][0]['ordType'] == 'Market':
                    event['data'][0]['price'] = self.socket.get_instrument()['midPrice']
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
                        'price': global_order.price,
                        'exchange': self.exchange_name,
                        'original_event': event
                        }

    async def on_order_handler(self, event):
        self.create_order(event['order'])

    async def on_cancel_handler(self, event):
        order_id = self._cancel_order_detector(event['price'])
        if order_id:
            self._cancel_order(order_id)
        else:
            print(f'Cancel rejected: Cant find necessary order in slave {self.exchange_name}')

    def _self_order_to_global(self, o) -> Order:
        if 'stopPx' not in o:
            o['stopPx'] = 0
        return Order(o['price'], o["orderQty"],
                     self.get_part(o['symbol'], o["orderQty"], o['price']),
                     o['orderID'],
                     self._self_pair_to_general(o['symbol']),
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

    def _cancel_order(self, order_id):
        result = self.connection.Order.Order_cancel(orderID=order_id).result()
        print(result)

    def create_order(self, order):
        quantity = self.calc_quantity_from_part(order.symbol, order.quantityPart, order.price)
        print(f"Slave {self.exchange_name}, balance: {self.get_balance()}; "
              f"Create Order: amount {quantity}, price: {order.price}  ")

        if order.type == 'MARKET':
            new_order = self.connection.Order.Order_new(symbol=self.translate(order.symbol),
                                                        side=self.translate(order.side),
                                                        orderQty=quantity,
                                                        stopPx=order.stop,
                                                        ordType=self.translate(order.type),
                                                        timeInForce='GoodTillCancel')
        else:
            new_order = self.connection.Order.Order_new(symbol=self.translate(order.symbol),
                                                        side=self.translate(order.side),
                                                        orderQty=quantity,
                                                        price=order.price,
                                                        stopPx=order.stop,
                                                        ordType=self.translate(order.type),
                                                        timeInForce='GoodTillCancel'
                                                        )
        print('order created:', new_order.result())

    async def close_position(self, symbol):
        print(f'close_position {symbol}')
        return self.connection.Order.Order_new(symbol=self.translate(symbol), ordType='Market', execInst='Close').result()


    def _pairs_transform_self(self, pairs):
        new_pairs = []
        for pair in pairs:
            if pair.strip() in self.translate_dict.keys():
                new_pairs.append(self.translate_dict[pair.strip()])
        return new_pairs

    def _self_pair_to_general(self, pair):
        reverse_dict = dict(zip(self.translate_dict.values(), self.translate_dict.keys()))
        return reverse_dict[pair]

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

    def translate(self, word) -> str:
        translate_dict = self.translate_dict
        if not word in translate_dict:
            translate_dict = dict(zip(translate_dict.values(), self.translate_dict.keys()))
            if not word in translate_dict:
                return word
        return translate_dict[word]
