class Exchange:
    balance = None
    exchange_name = None
    master_balance = None

    def __init__(self, apiKey, apiSecret, pairs, ):
        self.api = {'key': apiKey,
                    'secret': apiSecret}
        # delete '\n' from symbols'
        self.pairs = list(map(lambda pair: pair.replace('\n', ''), pairs))

    def get_balance(self):
        pass

    def get_trading_symbols(self):
        symbols = set()
        for pair in self.pairs:
            pair = str(pair)
            symbols.add(pair[:3])
            symbols.add(pair[3:])
        return symbols

    def get_open_orders(self):
        pass

    def cancel_order(self, symbol, orderId):
        pass

    def create_order(self, symbol, side, type, price, quantity):
        pass

    def get_balance_market_by_symbol(self, symbol):
        return list(filter(lambda el: el['asset'] == symbol[3:], self.get_balance()))[0]

    def get_balance_coin_by_symbol(self, symbol):
        return list(filter(lambda el: el['asset'] == symbol[:3], self.get_balance()))[0]




