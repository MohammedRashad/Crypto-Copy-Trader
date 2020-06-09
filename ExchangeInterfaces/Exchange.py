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

    def get_part(self, symbol, quantity, price, side):
        # get part of the total balance of this coin

        # if order[side] == sell: need obtain coin balance
        if side == 'BUY':
            balance = float(self.get_balance_market_by_symbol(symbol)['free'])
            part = float(quantity)*float(price)/balance
        else:
            balance = float(self.get_balance_coin_by_symbol(symbol)['free'])
            part = float(quantity)/balance

        part = part * 0.99  # decrease part for 1% for avoid rounding errors in calculation
        return part

    def calc_quantity_from_part(self, symbol, quantityPart, price, side):
        # calculate quantity from quantityPart

        # if order[side] == sell: need obtain coin balance
        if side == 'BUY':
            cur_bal = float(self.get_balance_market_by_symbol(symbol)['free'])
            quantity = float(quantityPart) * float(cur_bal) / float(price)
        else:
            cur_bal = float(self.get_balance_coin_by_symbol(symbol)['free'])
            quantity = quantityPart*cur_bal

        # balanceIndex = [idx for idx, element in enumerate(self.get_balance()) if element['asset'] == str(symbol)[3:]][0]
        # cur_bal = float(self.get_balance()[balanceIndex]['free'])
        quantity = round(quantity, 6)
        return quantity
