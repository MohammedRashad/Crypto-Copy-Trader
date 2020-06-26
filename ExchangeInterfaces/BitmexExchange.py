from .Exchange import Exchange
from bitmex_websocket import BitMEXWebsocket
from websocket import create_connection
import bitmex
import json
import platform
import os

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

    def update_balance(self):
        response = self.connection.User.User_getMargin().result()
        parsed_response = (json.loads(response))
        self.balance = parsed_response['availableMargin']

    async def on_order_handler(self, messege):
        print(messege)

    def get_open_orders(self):
        orders = self.connection.Order.Order_getOrders()
        open_orders = list(filter(lambda o: o['ordStatus'] == 'New', orders[0]))
        # positions = self.connection.Position.Position_get().result()
        # open_positions = list(filter(lambda o: o['isOpen'] == 'True', positions[0]))
        return open_orders

    def process_event(self, event):
        pass
