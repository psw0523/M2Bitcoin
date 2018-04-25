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

class KorbitExchange(Exchange):
    BASE_API_URL = "https://api.korbit.co.kr/v1"
    """
    Ripple, Bitcoin, Bitcoin Cash, Etherium, Etherium Classic, LiteCoin, Bitcoin Gold
    """
    TRADING_CURRENCY_TYPE = ["xrp_krw", "btc_krw", "bch_krw", "eth_krw",
            "etc_krw", "ltc_krw", "btg_krw"] 

    CURRENCY_MAP = { "BTC": "btc_krw", "ETH": "eth_krw", "LTC": "ltc_krw",
            "ETC": "etc_krw", "XRP": "xrp_krw", "BCH": "bch_krw", "BTG":
            "btg_krw" }

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        self.CLIENT_ID = config['KORBIT']['connect_key']
        self.CLIENT_SECRET = config['KORBIT']['secret_key']
        self.USER_NAME = config['KORBIT']['username']
        self.data_count = 10

    def get_ticker(self, currency_type=None):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.CURRENCY_MAP.keys():
            raise Exception('Not support currency type')

        my_currency = self.CURRENCY_MAP[currency_type]
        ticker_api_path = \
                "/ticker/detailed?currency_pair={currency}".format(currency=my_currency)
        url_path = self.BASE_API_URL + ticker_api_path
        res = requests.get(url_path)
        response_json = res.json()
        result={}
        result["timestamp"] = str(response_json['timestamp'])
        result["last"] = response_json['last']
        result["bid"] = response_json['bid']
        result["ask"] = response_json['ask']
        result["low"] = response_json['low']
        result["high"] = response_json['high']
        result["volume"] = response_json['volume']

        return result

    def get_orderbook(self, currency_type=None, count=10):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.CURRENCY_MAP.keys():
            raise Exception('Not support currency type')

        my_currency = self.CURRENCY_MAP[currency_type]
        orderbook_api_path = \
                "/orderbook?currency_pair={currency}".format(currency=my_currency)
        url_path = self.BASE_API_URL + orderbook_api_path
        res = requests.get(url_path)
        response_json = res.json()
        result={}
        result["timestamp"] = str(response_json['timestamp'])
        result["bids"] = response_json['bids']
        result["asks"] = response_json['asks']
        return result

    def get_recent(self, currency_type=None, count=10):
        if currency_type is None:
            raise Exception('Need to currency type')
        if currency_type not in self.CURRENCY_MAP.keys():
            raise Exception('Not support currency type')

        my_currency = self.CURRENCY_MAP[currency_type]
        recent_api_path = \
                "/transactions?currency_pair={currency}".format(currency=my_currency)
        url_path = self.BASE_API_URL + recent_api_path 
        res = requests.get(url_path)
        response_json = res.json()
        result = response_json
        return result

    def get_fee(self):
        return 0.08

    def get_states(self, currency):
        ticker = self.get_ticker(currency)
        orderbook = self.get_orderbook(currency)
        recents = self.get_recent(currency)

        states = []
        last = float(ticker['last'])
        volume = float(ticker['volume'])

        basis = last

        ## ticker
        # bid
        val = float(ticker['bid'])
        val = val / basis
        states.append(val)

        # ask
        val = float(ticker['ask'])
        val = val / basis 
        states.append(val)

        # high
        val = float(ticker['high'])
        val = val / basis 
        states.append(val)

        # low 
        val = float(ticker['low'])
        val = val / basis 
        states.append(val)

        ## orderbook
        bids = orderbook['bids']
        for bid in bids:
            q = float(bid[0])
            p = float(bid[1])
            p = p / basis
            q = q * p
            states.append(q)

        asks = orderbook['asks']
        for ask in asks:
            q = float(ask[0])
            p = float(ask[1])
            p = p / basis
            q = q * p
            states.append(q)

        ## recent
        i = 0
        for recent in recents:
            u = float(recent['amount'])
            p = float(recent['price'])
            p = p / last
            p = p * u
            states.append(p)
            i = i + 1
            if i > 20:
                break

        return last, volume ,states


if __name__ == "__main__":
    korbitExchange = KorbitExchange()
    currency = "BTC"
    # print(korbitExchange.get_ticker(currency))
    # print(korbitExchange.get_orderbook(currency))
    # print(korbitExchange.get_recent(currency))
    last, volume, states = korbitExchange.get_states(currency)
    print(len(states))
    print("------------------")
    print(states)
    # print(korbitExchange.get_states(currency))
