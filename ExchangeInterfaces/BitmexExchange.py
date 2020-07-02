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

    def __init__(self, apiKey, apiSecret, pairs):
        pairs = self._pairs_transform_slef(pairs)
        super().__init__(apiKey, apiSecret, pairs)
        self.exchange_name = "Bitmex"
        self.connection = bitmex.bitmex(api_key=apiKey, api_secret=apiSecret)
        self.update_balance()
        self.socket = None

    def start(self, caller_callback):
        self.socket = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol="XBTUSD",
                                      api_key=self.api['key'],
                                      api_secret=self.api['secret'], on_order_calback=caller_callback)
        self.socket.open_orders("")

        # pause system (temp solution)
        if platform.system() == "Windows":
            os.system("pause")
        elif platform.system() == "Linux":
            os.system('read -sn 1 -p "Press any key to continue..."')

    def stop(self):
        pass

    def update_balance(self):
        response = self.connection.User.User_getMargin().result()
        # parsed_response = (json.loads(response))
        self.balance = response[0]['availableMargin']

    async def on_order_handler(self, messege):
        print(messege)

    def get_open_orders(self):
        orders = self.connection.Order.Order_getOrders().result()
        open_orders = list(filter(lambda o: o['ordStatus'] == 'New', orders[0]))
        general_orders = []
        for o in open_orders:
            general_orders.append(
                self._self_order_to_global(o)
            )
        # positions = self.connection.Position.Position_get().result()
        # open_positions = list(filter(lambda o: o['isOpen'] == 'True', positions[0]))
        return general_orders

    def get_part(self, symbol, quantity, price):
        btc = float(quantity) / float(price)
        btc_satoshi = btc * (10 ** 8)
        part = float(btc_satoshi) / (float(self.get_balance()) + float(btc_satoshi))
        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, **kwargs):
        btc_satoshi = float(quantityPart) * float(self.get_balance())
        amount_usd = float(btc_satoshi) * float(price)
        return amount_usd

    def process_event(self, event):
        if event['action'] == "insert":
            if event['data'][0]['ordStatus'] == 'New':
                order = self._self_order_to_global(event['data'])
                return order

    def on_oreder_handler(self, event):
        pass
        # elif [event['action'] == 'update']:
        #     if event['data'][0]['ordStatus'] == 'Canceled':
        #
        #         order_id = self._cancel_order_detector()
        #         self.cancel_order()

    def _self_order_to_global(self, o) -> Order:
        return Order(o['price'], o["orderQty"],
                     self.get_part(o['symbol'], o["orderQty"], o['price']),
                     o['orderID'],
                     self._self_pair_to_general(o['symbol']),
                     o['side'].upper(),
                     o['ordType'].upper(),
                     self.exchange_name)

    def _cancel_order_detector(self, order):
        # detect order id which need to be canceled
        open_orders = self.get_open_orders()
        for ordr_open in open_orders:
            if ordr_open['price'] == order.price:
                return ordr_open['orderID']

    def cancel_order(self, order_id):
        self.connection.Order.Order_cancel(order_id)
        # self.connection.

    def create_order(self, symbol, side, type, price, quantity):
        pass

    def async_create_order(self, symbol, side, type, price, quantity, stop=0):
        self.create_order(symbol, side, type, price, quantity)

    def _pairs_transform_slef(self, pairs):
        new_pairs = []
        for pair in pairs:
            if pair.strip() in self.pairs_dicit.keys():
                new_pairs.append(self.pairs_dicit[pair.strip()])
        return new_pairs

    def _self_pair_to_general(self, pair):
        reverse_dict = dict(zip(self.pairs_dicit.values(), self.pairs_dicit.keys()))
        return reverse_dict[pair]

    pairs_dicit = {
        'BTCUSDT': 'XBTUSD',
        'ETHUSDT': 'ETHUSD',
        # 'BCHUSDT': 'BCHUSD',
        # 'TRXUSDT': 'TRXU20',
        # 'XRPUSDT': 'XRPUSD'
    }
