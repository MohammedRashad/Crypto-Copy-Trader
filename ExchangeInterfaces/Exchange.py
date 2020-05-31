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

    def get_part(self, symbol, quantity, price):
        cur_bal = list(filter(lambda el: el['asset'] == symbol[3:], self.get_balance()))[0]
        part = float(quantity)*float(price) / (float(cur_bal['free']))
        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quatity_from_part(self, symbol, quantityPart, price):
        # calculate quantity from quantityPart
        balanceIndex = [idx for idx, element in enumerate(self.get_balance()) if element['asset'] == str(symbol)[3:]][0]
        balance = float(self.get_balance()[balanceIndex]['free'])
        quantity = round((float(quantityPart) * float(balance) / float(price)), 6)
        return quantity
