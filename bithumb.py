import requests
import time
import datetime
import math
from exchange import Exchange
import configparser
import json
import base64
import hashlib
import hmac
import urllib
import numpy as np
from collections import OrderedDict

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
        self.old_records = []
        self.prev_ticker = {}
        self.ticker_list = []
        self.prev_recent = {}

    def reset(self):
        # self.old_records.clear()
        # self.prev_ticker = {}
        pass

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

    def records_to_states(self):
        states = []

        prev_volume = 0.0
        for record in self.old_records:
            start = float(record['start'])
            last = float(record['last']) / start
            states.append(last)
            bid = float(record['bid']) / start
            states.append(bid)
            ask = float(record['ask']) / start
            states.append(ask)
            high = float(record['high']) / start
            states.append(high)
            low = float(record['low']) / start
            states.append(low)
            volume = float(record['volume'])
            if prev_volume != 0.0:
                volume = volume - prev_volume
            else:
                volume = 0.0
            states.append(volume)
            prev_volume = volume

        return states

    def ticker_to_states(self, record):
        states = []

        start = float(record['start'])
        last = float(record['last']) / start
        states.append(last)
        bid = float(record['bid']) / start
        states.append(bid)
        ask = float(record['ask']) / start
        states.append(ask)
        high = float(record['high']) / start
        states.append(high)
        low = float(record['low']) / start
        states.append(low)

        return states
    
    def get_new_ticker(self, currency):
        time.sleep(1)
        ticker = self.get_ticker(currency)
        while True:
            if ticker is not None and ticker['last'] != self.prev_ticker['last']:
                break
            time.sleep(1)
            ticker = self.get_ticker(currency)

        return ticker

    def find_ticker_for_recent(self, recent):
        recent_date = recent['transaction_date']
        ticker_index = 0
        for ticker in self.ticker_list:
            ticker_date = ticker['date']
            if ticker_date == recent_date:
                self.ticker_list = self.ticker_list[ticker_index+1: ]
                return (ticker, ticker_index)
            ticker_index = ticker_index + 1

        return (None, ticker_index)

    def get_states(self, currency):
        while self.QUERY_RUNNING is True:
            time.sleep(0.3)

        self.QUERY_RUNNING = True

        found_recent = False
        ticker = {}
        recent = {}

        while found_recent is False:
            ticker = self.get_ticker(currency)
            ticker_date = datetime.datetime.fromtimestamp(int(ticker['timestamp'])/1000).strftime('%Y-%m-%d %H:%M:%S')
            ticker['date'] = ticker_date
            self.ticker_list.append(ticker)

            recent_list = self.get_recent(currency, 1)
            recent = recent_list[0]
            if len(self.prev_recent.keys()) == 0:
                ticker, ticker_index = self.find_ticker_for_recent(recent)
                if ticker is not None:
                    found_recent = True
            elif recent['cont_no'] != self.prev_recent['cont_no']:
                ticker, ticker_index = self.find_ticker_for_recent(recent)
                if ticker is not None:
                    found_recent = True

            self.prev_recent = recent
            time.sleep(0.3)

        self.QUERY_RUNNING = False

        # make states from ticker, recent
        # states

        start = float(ticker['start'])
        # last = float(ticker['last'])/start
        last = float(recent['price'])/start
        bid = float(ticker['bid'])/start
        ask = float(ticker['ask'])/start
        high = float(ticker['high'])/start
        low = float(ticker['low'])/start
        volume = float(recent['units_traded'])
        recent_type = 1 if recent['type'] == 'bid' else -1

        states = []
        states.append(last)
        states.append(bid)
        states.append(ask)
        states.append(high)
        states.append(low)
        states.append(volume)

        last = float(ticker['last'])
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

    # for n in bitThumbExchange.TRADE_CURRENCY_TYPE:
    #     states = bitThumbExchange.get_states(n)
    #     print("----------------------------------------------")
    #     print("Currency: " + n)
    #     print(states)

    # currency = "BTC"
    # currency = "ETH"
    # for i in range(0, 60):
    # for i in range(0, 1):
    #     time.sleep(1)
    #     print("i ====================>", i)
    #     recents = bitThumbExchange.get_recent(currency, 100)
    #     # orderbook = bitThumbExchange.get_orderbook(currency, 30)
    #     # print("recents------>")
    #     # print(recents)
    #
    #     history_ask = {}
    #     history_bid = {}
    #     for recent in recents:
    #         t = recent['type']
    #         u = float(recent['units_traded'])
    #         u = math.floor(u * 10000) / 10000
    #         p = float(recent['price'])
    #         if t == 'ask':
    #             print("ask")
    #             if p in history_ask.keys():
    #                 print(p, " += ", u)
    #                 history_ask[p] += u
    #             else:
    #                 print(p, " = ", u)
    #                 history_ask[p] = u
    #         elif t == 'bid':
    #             print("bid")
    #             if p in history_bid.keys():
    #                 print(p, " += ", u)
    #                 history_bid[p] += u
    #             else:
    #                 print(p, " = ", u)
    #                 history_bid[p] = u
    #
    #     od_ask = OrderedDict(sorted(history_ask.items()))
    #     od_bid = OrderedDict(sorted(history_bid.items()))
    #     print("recents--->")
    #     print(recents)
    #     print("ask ----->")
    #     print(history_ask)
    #     print(od_ask)
    #     print("bid ----->")
    #     print(history_bid)
    #     print(od_bid)

    currency = "ETH"

    prev_recent = {}
    ticker_dict = {}
    ticker_list = []
    for i in range(0, 120):
        recent_list = bitThumbExchange.get_recent(currency, 1)
        recent = recent_list[0]
        ticker = bitThumbExchange.get_ticker(currency)
        ticker_date = datetime.datetime.fromtimestamp(int(ticker['timestamp'])/1000).strftime('%Y-%m-%d %H:%M:%S')
        ticker['date'] = ticker_date
        # ticker_dict[ticker_date] = ticker
        ticker_list.append(ticker)
        # print(recent)

        new_recent = False
        if len(prev_recent.keys()) != 0:
            if recent['cont_no'] != prev_recent['cont_no']:
                print("--------------------")
                # print("cont_no: {}".format(recent['cont_no']))
                print("prev price; {}, recent price: {}, volume: {}, type: {}".format(prev_recent['price'], recent['price'],
                            recent['units_traded'], recent['type']))
                recent_date = recent['transaction_date']
                print("recent date: ", recent_date)
                ticker = None
                found_ticker = False
                ticker_index = 0
                for ticker in ticker_list:
                    ticker_date = ticker['date']
                    # if ticker_date == recent_date and ticker['last'] == recent['price']:
                    if ticker_date == recent_date:
                        found_ticker = True
                        break
                    ticker_index = ticker_index + 1

                if found_ticker:
                    print("ticker price: {}, bid: {}, ask: {}".format(ticker['last'],
                            ticker['bid'], ticker['ask']))
                    # ticker_dict.pop(recent['transaction_date'])
                    ticker_list = ticker_list[ticker_index + 1: ]
                else:
                    print("ticker is None for ", recent['transaction_date'])
                    # print(ticker_dict)
                    print(ticker_list)
                # print(ticker)

        prev_recent = recent

        time.sleep(0.3)

    # print("ticker_dict ----> ", ticker_dict)
    print("ticker_list length ----> ", len(ticker_list))

    # prev_ticker = {}
    # for i in range(0, 60):
    #     ticker = bitThumbExchange.get_ticker(currency)
    #     recents = bitThumbExchange.get_recent(currency)
    #     print("i ==================>", i)
    #     # print(ticker)
    #     # print(recents)
    #
    #     if len(prev_ticker.keys()) > 0:
    #         prev_ticker_timestamp = int(prev_ticker['timestamp'])
    #         prev_ticker_timestamp = int(prev_ticker_timestamp/1000)
    #         prev_ticker_datetime = datetime.datetime.fromtimestamp(prev_ticker_timestamp)
    #         fmt_str = "[{}] datetime: {}, timestamp: {}, price: {}, ask: {}, bid: {}"
    #         print(fmt_str.format("PREV", prev_ticker_datetime, prev_ticker_timestamp,
    #             float(prev_ticker['last']), float(prev_ticker['ask']), float(prev_ticker['bid'])))
    #
    #         ticker_timestamp = int(ticker['timestamp'])
    #         ticker_timestamp = int(ticker_timestamp/1000)
    #         ticker_datetime = datetime.datetime.fromtimestamp(ticker_timestamp)
    #         print(fmt_str.format("CURR", ticker_datetime, ticker_timestamp,
    #             float(ticker['last']), float(ticker['ask']), float(ticker['bid'])))
    #         
    #         processed_recents = []
    #         for recent in recents:
    #             processed_recent = {}
    #             s = recent['transaction_date']
    #             u = float(recent['units_traded'])
    #             timestamp = time.mktime(datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timetuple())
    #             processed_recent['date'] = s
    #             processed_recent['timestamp'] = int(timestamp)
    #             processed_recent['type'] = recent['type']
    #             processed_recent['volume'] = u
    #             processed_recent['price'] = recent['price']
    #             processed_recents.append(processed_recent)
    #
    #         print(processed_recents)
    #
    #     prev_ticker = ticker
    #
    #     time.sleep(1)
