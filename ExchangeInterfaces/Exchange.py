class Exchange:
    balance = None
    exchange_name = None
    master_balance = None

    def __init__(self, apiKey, apiSecret, pairs, master_balance=None):
        self.api = {'key': apiKey,
                    'secret': apiSecret}
        # delete '\n' from symbols'
        self.pairs = list(map(lambda pair: pair.replace('\n', ''), pairs))
        self.master_balance = master_balance

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

    def create_socket(self):
        print('websocket for this exchange ' + self.exchange_name + ' is not supported now')

    def create_order(self, symbol, side, type, price, quantity):
        pass

    def get_part(self, symbol, price, origQty, master_balance=None):
        # calculate the part becomes the size of the order from the balance
        if not self.master_balance is None:
            pass
        elif not master_balance is None :
            self.master_balance = master_balance
        else:
            print('wrong usage function get_part(), '
                  'if need to call from rest api, give master_balance argument')
            exit(-5)
        for value in self.master_balance:
            if (value['asset'] == str(symbol)[3:]):
                part = float(float(origQty) * float(price))
                part = part / float(float(value['free']) + float(value['locked']))
                return part


    def calc_quatity_from_part(self, symbol, quantityPart, price):
        # calculate quantity from quantityPart
        balanceIndex = [idx for idx, element in enumerate(self.get_balance()) if element['asset'] == str(symbol)[3:]][0]
        balance = float(self.get_balance()[balanceIndex]['free']) + float(self.get_balance()[balanceIndex]['locked'])
        quantity = round((float(quantityPart) * float(balance) / float(price)), 6)
        return quantity
