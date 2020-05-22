class Exchange:
    balance = None
    exchange_name = None

    def __init__(self, apiKey, apiSecret, pairs):
        self.api = {'key': apiKey,
               'secret': apiSecret}
        self.pairs = pairs

    def get_balance(self):
        pass

    def get_trading_symbols(self):
        symbols = set()
        for pair in self.pairs:
            pair = str(pair)
            symbols.add(pair[:3])
            symbols.add(pair[3:-1])
        return symbols

    def get_open_orders(self):
        pass

    def cancel_order(self):
        pass

    def create_order(self, symbol, side, type, price, quantity):
        pass
