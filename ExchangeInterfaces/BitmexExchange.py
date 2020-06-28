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
        super().__init__(apiKey, apiSecret, pairs)
        self.exchange_name = "Binance"
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
            quantityPart = self.get_part(o['symbol'], o["origQty"], o['price'], o['side'])
            general_orders.append(Order(o['price'], o["origQty"],
                                        quantityPart, o['orderId'], o['symbol'], o['side'], o['type'],
                                        self.exchange_name))
        # positions = self.connection.Position.Position_get().result()
        # open_positions = list(filter(lambda o: o['isOpen'] == 'True', positions[0]))
        return open_orders

    def get_part(self, quantity, price):
         ticker = self.socket.get_ticker()
         pass

    def process_event(self, event):
        print(event)

    def _cancel_order_detector(self, event):
        # detect order id which need to be canceled
        open_orders = self.get_open_orders()
        for ordr_open in open_orders:
            if ordr_open['price'] == event['p']:
                return ordr_open['orderId']

    def cancel_order(self, symbol, orderId):
        pass
        # self.connection.

    def create_order(self, symbol, side, type, price, quantity):
        pass

    def async_create_order(self, symbol, side, type, price, quantity, stop=0):
        self.create_order(symbol, side, type, price, quantity)
