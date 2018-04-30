import requests
import time
import math
from exchange import Exchange
import configparser
import json
import base64
import hashlib
import hmac
import urllib
import numpy as np

class BithumbExchange(Exchange):
    BASE_API_URL = "https://api.bithumb.com"
    TRADE_CURRENCY_TYPE = ["BTC", "ETH", "DASH", "LTC", "ETC", "XRP", "BCH",
            "XMR", "ZEC", "QTUM", "BTG", "EOS", "ICX", "VEN", "TRX", "ELF",
            "MCO", "MITH", "OMG", "KNC"]
    TRADE_UNIT = {"BTC": 1000, "ETH": 500, "DASH": 500, "LTC": 100, "ETC": 10,
            "XRP": 1, "BCH": 1000, "XMR": 100, "ZEC": 100, "QTUM": 10, 
            "BTG": 50, "EOS": 5, "ICX": 1, "VEN": 1, "TRX": 1, "ELF": 1,
            "MCO": 5, "MITH": 1, "OMG": 10, "KNC": 1}

    QUERY_RUNNING = False

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        self.CLIENT_ID = config['BITHUMB']['connect_key']
        self.CLIENT_SECRET = config['BITHUMB']['secret_key']
        self.USER_NAME = config['BITHUMB']['username']
        self.data_count = 20

    def get_ticker(self, currency_type=None):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.TRADE_CURRENCY_TYPE:
            raise Exception('Not support currency type')

        ticker_api_path = "/public/ticker/{currency}".format(currency=currency_type)
        url_path = self.BASE_API_URL + ticker_api_path
        res = requests.get(url_path)
        try:
            response_json = res.json()
        except json.decoder.JSONDecodeError as e:
            print(e)
            return None
        else:
            result={}
            result["timestamp"] = str(response_json['data']["date"])
            result["start"] = response_json['data']["opening_price"]
            result["last"] = response_json['data']["closing_price"]
            result["bid"] = response_json['data']["buy_price"]
            result["ask"] = response_json['data']["sell_price"]
            result["high"] = response_json['data']["max_price"]
            result["low"] = response_json['data']["min_price"]
            result["average"] = response_json['data']["average_price"]
            result["volume"] = response_json['data']["volume_1day"]
            # units same to volume
            # result["units"] = response_json['data']["units_traded"]
            result["volume7"] = response_json['data']["volume_7day"]
            return result

    def get_orderbook(self, currency_type=None, count=10):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.TRADE_CURRENCY_TYPE:
            raise Exception('Not support currency type')

        orderbook_api_path = \
                "/public/orderbook/{currency}?count={count}".format(currency=currency_type, count=count)
        url_path = self.BASE_API_URL + orderbook_api_path
        res = requests.get(url_path)
        try:
            response_json = res.json()
        except json.decoder.JSONDecodeError as e:
            print(e)
            return None
        else:
            result={}
            result["timestamp"] = str(response_json['data']["timestamp"])
            result["bids"] = response_json['data']['bids']
            result["asks"] = response_json['data']['asks']
            return result

    def get_recent(self, currency_type=None, count=10):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.TRADE_CURRENCY_TYPE:
            raise Exception('Not support currency type')

        recent_api_path = \
                "/public/recent_transactions/{currency}?count={count}".format(currency=currency_type, count=count)
        url_path = self.BASE_API_URL + recent_api_path
        res = requests.get(url_path)
        try:
            response_json = res.json()
        except json.decoder.JSONDecodeError as e:
            print(e)
            return None
        else:
            result = response_json['data']
        return result

    def get_fee(self):
        return 0.15

    def get_states(self, currency):
        while self.QUERY_RUNNING is True:
            time.sleep(1)

        self.QUERY_RUNNING = True

        ticker = self.get_ticker(currency)
        while ticker is None:
            time.sleep(1)
            ticker = self.get_ticker(currency)

        orderbook = self.get_orderbook(currency, self.data_count)
        while orderbook is None:
            time.sleep(1)
            orderbook = self.get_orderbook(currency, self.data_count)

        price = int(ticker['last'])
        trade_unit = self.TRADE_UNIT[currency]

        bid_states = {}
        ask_states = {}

        for i in range(0, self.data_count):
            c = price - i * trade_unit
            bid_states[str(c)] = 0.0

        for i in range(0, self.data_count):
            c = price + i * trade_unit
            ask_states[str(c)] = 0.0

        bids = orderbook['bids']
        for bid in bids:
            # print("bid: ", bid)
            if bid['price'] in bid_states.keys():
                bid_states[bid['price']] = bid['quantity']

        # print(bid_states)
        bid_values = []
        for bid in bid_states.values():
            bid_values.append(float(bid))

        # print(bid_values)
        np_bids = np.array(bid_values)
        mean = np.mean(np_bids)
        np_bids = np_bids / mean
        # print("bids --->")
        # print(np_bids)

        asks = orderbook['asks']
        # print("asks order")
        # print(asks)
        for ask in asks:
            if ask['price'] in ask_states.keys():
                ask_states[ask['price']] = ask['quantity']

        # print(ask_states)
        ask_values = []
        for ask in ask_states.values():
            ask_values.append(float(ask))

        # print(ask_values)
        np_asks = np.array(ask_values)
        mean = np.mean(np_asks)
        np_asks = np_asks / mean
        # print("asks --->")
        # print(np_asks)

        states = np_bids.tolist() + np_asks.tolist()
        last = float(ticker['last'])
        volume = float(ticker['volume'])

        self.QUERY_RUNNING = False

        return last, volume, states


if __name__ == "__main__":
    bitThumbExchange = BithumbExchange()
    # print("get_ticker results ------------------")
    # for n in bitThumbExchange.TRADE_CURRENCY_TYPE:
    #     print(n, " --> ", bitThumbExchange.get_ticker(n))
    # print("get_orderbook results ------------------")
    # for n in bitThumbExchange.TRADE_CURRENCY_TYPE:
    #     print(n, " --> ", bitThumbExchange.get_orderbook(n, 10))
    # print("get_recent results ------------------")
    # for n in bitThumbExchange.TRADE_CURRENCY_TYPE:
    #     print(n, " --> ", bitThumbExchange.get_recent(n, 10))
    # currency = "BTC"
    # count = 20
    # print("get_ticker results ------------------")
    # print(bitThumbExchange.get_ticker(currency))
    # print("get_orderbook results ------------------")
    # print(bitThumbExchange.get_orderbook(currency, count))
    # print("get_recent results ------------------")
    # print(bitThumbExchange.get_recent(currency, count))
    # ticker = bitThumbExchange.get_ticker(currency)
    # print("Current Price: ", ticker['last'])
    # print("Current Volume: ", ticker['volume'])

    # for n in bitThumbExchange.TRADE_CURRENCY_TYPE:
    #     bid_states = {}
    #     ask_states = {}
    #
    #     ticker = bitThumbExchange.get_ticker(n)
    #     print("-----------------------------------------------")
    #     print("CURRENCY ===> ", n)
    #     print("Current Price: ", ticker['last'])
    #     print("Current Volume: ", ticker['volume'])
    #     
    #     price = int(ticker['last'])
    #     trade_unit = bitThumbExchange.TRADE_UNIT[n]
    #
    #     for i in range(0, 20):
    #         c = price - i * trade_unit
    #         bid_states[str(c)] = 0.0
    #
    #     for i in range(0, 20):
    #         c = price + i * trade_unit
    #         ask_states[str(c)] = 0.0
    #
    #     # print(ask_states)
    #
    #     orderbook = bitThumbExchange.get_orderbook(n, 20)
    #
    #     bids = orderbook['bids']
    #     for bid in bids:
    #         # print("bid: ", bid)
    #         if bid['price'] in bid_states.keys():
    #             bid_states[bid['price']] = bid['quantity']
    #
    #     # print(bid_states)
    #     bid_values = []
    #     for bid in bid_states.values():
    #         bid_values.append(float(bid))
    #
    #     # print(bid_values)
    #     np_bids = np.array(bid_values)
    #     mean = np.mean(np_bids)
    #     np_bids = np_bids / mean
    #     print("bids --->")
    #     print(np_bids)
    #
    #     asks = orderbook['asks']
    #     # print("asks order")
    #     # print(asks)
    #     for ask in asks:
    #         if ask['price'] in ask_states.keys():
    #             ask_states[ask['price']] = ask['quantity']
    #
    #     # print(ask_states)
    #     ask_values = []
    #     for ask in ask_states.values():
    #         ask_values.append(float(ask))
    #
    #     # print(ask_values)
    #     np_asks = np.array(ask_values)
    #     mean = np.mean(np_asks)
    #     np_asks = np_asks / mean
    #     print("asks --->")
    #     print(np_asks)

    for n in bitThumbExchange.TRADE_CURRENCY_TYPE:
        states = bitThumbExchange.get_states(n)
        print("----------------------------------------------")
        print("Currency: " + n)
        print(states)
