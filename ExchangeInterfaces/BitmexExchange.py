from .Exchange import Exchange
# from bitmex_websocket import BitMEXWebsocket
from Helpers.Bitmex_websocket_mod import BitMEXWebsocket_mod as BitMEXWebsocket
import bitmex
from Helpers.Order import Order
import Actions.Actions as Actions


# TEST_BITMEX_URL = "wss://testnet.bitmex.com"
# BITMEX_URL = "wss://www.bitmex.com"

class BitmexExchange(Exchange):
    exchange_name = "Bitmex"
    isMargin = True
    ENDPOINT = "https://www.bitmex.com/api/v1"
    TEST = False

    def __init__(self, apiKey, apiSecret, pairs, name):

        super().__init__(apiKey, apiSecret, pairs, name)
        self.pairs = list(map(lambda pair: self.translate(pair) if pair != self.translate(pair)
        else self.logger.debug(f"Can't translate word {pair} in {self.exchange_name}"), self.pairs))
        self.pairs = list(filter(None, self.pairs))
        self.connection = bitmex.bitmex(api_key=apiKey, api_secret=apiSecret, test=self.TEST)
        self.socket = {}
        # self.firts_copy_flag = True
        self.balance_updated = False
        for pair in self.pairs:
            if pair == 'XBTUSD':
                self.socket['XBTUSD'] = BitMEXWebsocket(endpoint=self.ENDPOINT, symbol='XBTUSD',
                                                        api_key=self.api['key'],
                                                        api_secret=self.api['secret'],
                                                        on_balance_update=self.on_balance_update)
            else:
                self.socket[pair] = BitMEXWebsocket(endpoint=self.ENDPOINT, symbol=pair,
                                                api_key=self.api['key'],
                                                api_secret=self.api['secret']
                                                )

    def start(self, caller_callback):
        self.stop()
        self.socket['XBTUSD'] = BitMEXWebsocket(endpoint=self.ENDPOINT, symbol='XBTUSD',
                                                api_key=self.api['key'],
                                                api_secret=self.api['secret'], on_balance_update=self.on_balance_update,
                                                on_order_calback=caller_callback)
        for pair in self.pairs:
            if pair == 'XBTUSD':
                continue
            self.socket[pair] = BitMEXWebsocket(endpoint=self.ENDPOINT, symbol=pair,
                                                api_key=self.api['key'],
                                                api_secret=self.api['secret'], on_order_calback=caller_callback,
                                                )

    def stop(self):
        for socket in self.socket:
            self.socket[socket].exit()

    def on_balance_update(self, event):
        if 'availableMargin' in event:
            self.balance = event['availableMargin'] / (10**8) * (self.socket['XBTUSD'].get_instrument()['midPrice']\
            if "XBTUSD" in self.socket else self.connection.Instrument.Instrument_get(symbol='XBTUSD', count=1, reverse=True).result()[0][0]['midPrice'])

            self.balance_updated = True

    def update_balance(self):
        self.balance = self.socket['XBTUSD'].funds()['availableMargin'] / 10**8 *\
                       self.socket['XBTUSD'].get_instrument()['midPrice']

    def get_open_orders(self):
        open_orders = []
        for pair in self.pairs:
            open_orders += self.socket[pair].open_orders(clOrdIDPrefix="")

        general_orders = []
        for o in open_orders:
            general_orders.append(self._self_order_to_global(o))
        return general_orders

    def get_part(self, symbol,  quantity: float, price: float):
        # btc = float(quantity) / float(price)
        # btc_satoshi = btc * (10 ** 8)

        usd_order_value = quantity

        balance = self.get_balance()
        # if self.balance_updated:
        #     part = usd_order_value / float(balance + usd_order_value)
        # else:
        #     part = usd_order_value / balance
        part = usd_order_value / balance
        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, **kwargs):
        amount_usd = float(quantityPart) * float(self.get_balance())
        # btc = btc_satoshi / (10 ** 8)
        # amount_usd = float(btc) * float(price)
        return amount_usd

    def process_event(self, event):
        # self.update_balance()
        self.balance_updated = False

        if event['action'] == "insert":

            check_result = self.check_expected_order(event)
            if check_result:
                return check_result

            data = event['data'][0]
            if data['ordStatus'] == 'New' \
                    or (data['ordStatus'] == 'Filled' and 'ordType' in data):
                if event['data'][0]['execInst'] == 'Close':
                    # order to close position came
                    close_order = event['data'][0]

                    if close_order['ordType'] == 'Market':
                        price = None
                    else:
                        price = close_order['price']

                    return Actions.ActionClosePosition(
                        self.translate(close_order['symbol']),
                        self.translate(close_order['ordType']),
                        price,
                        close_order['orderID'],
                        self.exchange_name,
                        event
                    )
                else:
                    order = self._self_order_to_global(event['data'][0])

                    return Actions.ActionNewOrder(
                        order,
                        self.exchange_name,
                        event)

        elif event['action'] == 'update':
            if 'ordStatus' not in event['data'][0]:
                return
            if event['data'][0]['ordStatus'] == 'Canceled':
                orders = self.socket[event['data'][0]['symbol']].open_orders(clOrdIDPrefix="")
                order = list(filter(lambda o: o['orderID'] == event['data'][0]['orderID'],
                                    orders))[0]
                global_order = self._self_order_to_global(order)
                return Actions.ActionCancel(
                    global_order.symbol,
                    global_order.price,
                    global_order.id,
                    self.exchange_name,
                    event
                )

    async def on_order_handler(self, event: Actions.ActionNewOrder):
        self.create_order(event.order)

    async def on_cancel_handler(self, event: Actions.ActionCancel):
        if self.is_program_order(event.order_id):
            order_id = None
            clOrderId = event.order_id
        else:
            order_id = self._cancel_order_detector(event.price)
            clOrderId = None

        if order_id or clOrderId:
            self._cancel_order(order_id, clOrderId)
        else:
            self.logger.error(f'Cancel rejected: Cant find necessary order in slave {self.name}')

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
        try:
            if clOrderID:
                result = self.connection.Order.Order_cancel(clOrdID=clOrderID).result()
            else:
                result = self.connection.Order.Order_cancel(orderID=order_id).result()
            self.logger.info(f'{self.name}: Cancel order request send. Response: {result}')
            self.logger.info(f'{self.name}: Order canceled')
        except:
            self.logger.exception(f'{self.name}: Error cancel order')

    def create_order(self, order: Order):
        try:
            quantity = self.calc_quantity_from_part(order.symbol, order.quantityPart,
                                                    self.socket['XBTUSD'].get_instrument()['midPrice'])

            self.logger.info(f"Slave {self.name}, balance: {self.get_balance()}; "
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
            self.logger.info(f'{self.name} Create order request send')
            self.logger.debug(f'Response: {new_order.result()} ')
        except:
            self.logger.exception(f'{self.name}: Error create order')

    async def close_position(self, event: Actions.ActionClosePosition):
        self.logger.info(f'{self.name}: close_position {event.symbol}')

        if event.order_type == 'MARKET':
            return self.connection.Order.Order_new(symbol=self.translate(event.symbol), ordType='Market',
                                                   execInst='Close').result()
        else:
            self.ids.append(event.order_id)
            return self.connection.Order.Order_new(symbol=self.translate(event.symbol), ordType='Limit',
                                                   price=event.price,
                                                   execInst='Close',
                                                   clOrdID=event.order_id).result()

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
