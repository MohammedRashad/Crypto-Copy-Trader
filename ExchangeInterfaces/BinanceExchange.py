from .Exchange import Exchange
from binance.client import Client
from binance.websockets import BinanceSocketManager


class BinanceExchage(Exchange):

    def __init__(self, apiKey, apiSecret, pairs, master_balance=None):
        super().__init__(apiKey, apiSecret, pairs, master_balance)
        self.exchange_name = "Binance"
        self.connection = Client(self.api['key'], self.api['secret'])
        self.update_balance()

    def update_balance(self):
        account_information = self.connection.get_account()
        symbols = self.get_trading_symbols()
        newDict = list(filter(lambda elem: str(elem['asset']) in symbols, account_information['balances']))
        self.balance = newDict

    def get_balance(self):
        return self.balance

    def get_open_orders(self):
        return self.connection.get_open_orders()

    def cancel_order(self, symbol, orderId):
        self.connection.cancel_order(symbol=symbol, orderId=orderId)
        print('order canceled')

    def _cancel_order_detector(self, event):
        # detect order id which need to be canceled
        slave_open_orders = self.connection.get_open_orders()
        for ordr_open in slave_open_orders:
            if ordr_open['price'] == event['p']:
                return ordr_open['orderId']


    def create_socket(self):
        bm = BinanceSocketManager(self.connection)
        return bm

    def on_order_handler(self, event):
        # shortcut mean https://github.com/binance-exchange/binance-official-api-docs/blob/master/user-data-stream.md#order-update
        if event['e'] == "executionReport":
            print(event)
            if event['s'] in self.pairs:
                if event['x'] == 'CANCELED':
                    slave_order_id = self._cancel_order_detector(event)
                    self.cancel_order(event['s'], slave_order_id)
                else:
                    self.create_order(event['s'],
                                      event['S'],
                                      event['o'],
                                      event['p'],
                                      self.get_part(event['s'], event['p'], event['q']),
                                      event['f'],
                                      event['P']
                                      )



    def create_order(self, symbol, side, type, price, quantityPart, timeInForce, stopPrice=0):
        """
        :param symbol:
        :param side:
        :param type: LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, LIMIT_MAKER
        :param price: required if limit order
        :param quantityPart: the part that becomes an order from the entire balance
        :param timeInForce: required if limit order
        :param stopPrice: required if type == STOP_LOSS or TAKE_PROFIT
        """
        quantity = self.calc_quatity_from_part(symbol, quantityPart, price)
        try:
            if (type == 'STOP_LOSS_LIMIT' or type == "TAKE_PROFIT_LIMIT"):
                self.connection.create_order(symbol=symbol,
                                             side=side,
                                             type=type,
                                             price=price,
                                             quantity=quantity,
                                             timeInForce=timeInForce,
                                             stopPrice=stopPrice)
            if (type == 'MARKET'):
                self.connection.create_order(symbol=symbol,
                                             side=side,
                                             type=type,
                                             quantity=quantity)
            else:
                self.connection.create_order(symbol=symbol,
                                             side=side,
                                             type=type,
                                             quantity=quantity,
                                             price=price,
                                             timeInForce=timeInForce)
            print("order created")
        except Exception as e:
            print(str(e))