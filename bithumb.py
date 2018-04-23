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

class BithumbExchange(Exchange):
    BASE_API_URL = "https://api.bithumb.com"
    TRADE_CURRENCY_TYPE = ["BTC", "ETH", "DASH", "LTC", "ETC", "XRP", "BCH",
            "XMR", "ZEC", "QTUM", "BTG", "EOS", "ICX", "VEN", "TRX", "ELF",
            "MITH"]

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        self.CLIENT_ID = config['BITHUMB']['connect_key']
        self.CLIENT_SECRET = config['BITHUMB']['secret_key']
        self.USER_NAME = config['BITHUMB']['username']

    def get_ticker(self, currency_type=None):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.TRADE_CURRENCY_TYPE:
            raise Exception('Not support currency type')

        ticker_api_path = "/public/ticker/{currency}".format(currency=currency_type)
        url_path = self.BASE_API_URL + ticker_api_path
        res = requests.get(url_path)
        response_json = res.json()
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
        response_json = res.json()
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
        response_json = res.json()
        result = response_json['data']
        return result

    def get_fee(self):
        return 0.15

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
    currency = "BTC"
    count = 20
    print("get_ticker results ------------------")
    print(bitThumbExchange.get_ticker(currency))
    print("get_orderbook results ------------------")
    print(bitThumbExchange.get_orderbook(currency, count))
    print("get_recent results ------------------")
    print(bitThumbExchange.get_recent(currency, count))
