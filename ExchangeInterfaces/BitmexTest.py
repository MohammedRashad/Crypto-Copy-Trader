from ExchangeInterfaces.BitmexExchange import BitmexExchange


class BitmexTest(BitmexExchange):
    ENDPOINT = "https://testnet.bitmex.com/api/v1"
    TEST = True
