from .Exchange import Exchange
from binance.client import Client

class BinanceExchage(Exchange):

    def __init__(self, apiKey, apiSecret, pairs):
        super().__init__(apiKey, apiSecret, pairs)
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

    def create_order(self, symbol, side, type, price, quantityPart, timeInForce, stopPrice = 0):
        """
        :param symbol:
        :param side:
        :param type: LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, LIMIT_MAKER
        :param price: required if limit order
        :param quantityPart: the part that becomes an order from the entire balance
        :param timeInForce: required if limit order
        :param stopPrice: required if type == STOP_LOSS or TAKE_PROFIT
        """
        # calculate quantity from quantityPart
        balanceIndex = [idx for idx, element in enumerate( self.get_balance()) if element['asset'] == str(symbol)[3:]][0]
        balance = float(self.get_balance()[balanceIndex]['free']) + float(self.get_balance()[balanceIndex]['locked'])
        quantity = round((float(quantityPart) * float(balance) / float(price) ), 6)

        if (type == 'STOP_LOSS_LIMIT' or  type == "TAKE_PROFIT_LIMIT"):
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
        else :
            self.connection.create_order(symbol=symbol,
                            side=side,
                            type=type,
                            quantity=quantity,
                            price = price ,
                            timeInForce=timeInForce)

