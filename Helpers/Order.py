class Order:
    def __init__(self, price, amount, quantityPart, order_id, symbol, side, order_type, exchange, stop=0):
        self.price = price
        self.amount = amount
        self.quantityPart = quantityPart
        self.id = order_id
        self.symbol = symbol
        self.side = side
        self.type = order_type
        self.exchange = exchange
        self.stop = stop

    def __str__(self):
        return f"Order: id: {self.id}"  \
               f"price: {self.price}," \
               f" symbol: {self.symbol}," \
               f" amount: {self.amount}," \
               f" part: {self.quantityPart}," \
               f" side: {self.side}," \
               f" type: {self.type},"

    def __repr__(self):
        return self.__str__()
