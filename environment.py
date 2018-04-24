import time
import numpy as np
import math
#  from exchange import Exchange
from bithumb import BithumbExchange


DO_NOTHING = 0
BUY = 1
SELL = 2

class Env():
    def __init__(self, initial_investment, exchange="Bithumb", currency="BTC", percent_per_trade=0.05):
        """
        initial_investment: 초기 투자금
        cash_asset: 보유 현금
        average_cost: 평단
        buy_count: 보유 물량
        current_price: 현재 가격
        cash_per_trade: 한번 거래에 사용하는 현금
        fee_percent: 수수료 비율
        earning_rate: 현재 수익률
        """
        self.exchange = BithumbExchange()
        self.currency = currency

        # account information
        self.initial_investment = initial_investment
        self.cash_asset = self.initial_investment
        self.average_cost = 0
        self.buy_count = 0.0
        self.current_price = 0
        self.cash_per_trade = self.initial_investment * percent_per_trade
        self.fee_percent = self.exchange.get_fee()
        self.earning_rate = 0.0
        self.fee_sum = 0
        self.done = False

        self.data_count = 20
        _, states = self.get_states()
        self.states_size = len(states)
        self.action_dict = { DO_NOTHING: "DoNothing", BUY: "Buy", SELL: "Sell" }

    def reset(self):
        """
        return state(object)
        """
        self.cash_asset = self.initial_investment
        self.average_cost = 0
        self.buy_count = 0.0
        self.current_price = 0
        self.earning_rate = 0.0
        self.fee_sum = 0
        self.done = False

        self.current_price, states = self.get_states()
        return states

    def do_nothing(self):
        reward = 0.0

        # if self.buy_count > 0:
        #     if self.average_cost > self.current_price:
        #         reward = -0.0001
        # else:
        #     reward = -0.00001

        return reward

    def buy(self):
        buy_count = 0.0
        buy_price = 0.0
        reward = 0.0
        real_price = 0.0
        cash_trade = 0
        fee_per_unit = 0.0

        if self.cash_asset > self.cash_per_trade:
            cash_trade = self.cash_per_trade
        else:
            cash_trade = self.cash_asset

        fee_per_unit = self.current_price * self.fee_percent * 0.01
        real_price = self.current_price + fee_per_unit

        buy_count = cash_trade / real_price
        buy_count = math.floor(buy_count * 100) / 100

        buy_price = int(buy_count * real_price)
        fee = int(buy_count * fee_per_unit)

        if buy_count > 0:
            self.cash_asset -= buy_price
            total_buy_cost = self.buy_count * self.average_cost + self.current_price * buy_count
            self.buy_count += buy_count
            self.buy_count = math.floor(self.buy_count * 100) / 100
            self.average_cost = int(total_buy_cost / self.buy_count)
            self.fee_sum += fee
        else:
            if self.buy_count <= 0:
                self.done = True
            reward = -0.01
            
        return reward

    def sell(self):
        sell_count = 0.0
        reward = 0.0
        cash_trade = 0
        earning_rate = 0.0

        sell_count = self.cash_per_trade / self.current_price
        if self.buy_count < sell_count:
            sell_count = self.buy_count
        sell_count = math.floor(sell_count * 100) / 100

        sell_price = int(sell_count * self.current_price)

        if sell_count > 0:
            self.buy_count -= sell_count
            self.buy_count = math.floor(self.buy_count * 100) / 100
            self.cash_asset += sell_price

            # calculate earning_rate
            # earning_rate = ((평단 * 수량 + 현금) - 초기투자금)/초기투자금
            earning_rate = ((self.average_cost * self.buy_count + self.cash_asset) - self.initial_investment) / self.initial_investment
            reward = earning_rate - self.earning_rate
            self.earning_rate = earning_rate

            if self.buy_count <= 0:
                self.buy_count = 0.0
                self.average_cost = 0
        else:
            if self.cash_asset <= 0:
                self.done = True
            reward = -0.01

        return reward

    def step(self, action):
        """
        return state(object), reward(float), done(bool), info(dict)
        """
        self.current_price, states = self.get_states()
        reward = 0.0
        info = {}

        if action == DO_NOTHING:
            reward = self.do_nothing()
        elif action == BUY:
            reward = self.buy()
        elif action == SELL:
            reward = self.sell()

        info['initial_investment'] = self.initial_investment
        info['cash_asset'] = self.cash_asset
        info['average_cost'] = self.average_cost
        info['buy_count'] = self.buy_count
        info['current_price'] = self.current_price
        info['cash_per_trade'] = self.cash_per_trade
        info['fee_percent'] = self.fee_percent
        info['earning_rate'] = self.earning_rate
        info['last_action'] = self.action_dict[action]
        info['fee_sum'] = self.fee_sum
        info['last_reward'] = reward
        info['done'] = self.done

        total_asset = self.cash_asset + self.average_cost * self.buy_count
        total_cost = self.fee_sum
        # print("total_asset ---------> ", total_asset)
        # print("total_cost ----------> ", total_cost)
        print("calculate investment -> ", total_asset + total_cost)
        print("initial_investment ---> ", self.initial_investment)

        print(info)

        return states, reward, self.done, info

    def state_size(self):
        return self.states_size

    def action_size(self):
        # 0: do nothing, 1: buy, 2: sell
        return 3

    def get_states(self):
        time.sleep(1)
        ticker = self.exchange.get_ticker(self.currency)
        orderbook = self.exchange.get_orderbook(self.currency, self.data_count)
        #  recents = self.exchange.get_recent(self.currency, self.data_count)

        states = []
        average = float(ticker['average'])
        last = float(ticker['last'])

        ## ticker
        # start
        val = float(ticker['start'])
        if val < average:
            val = -val
        val = val / average
        states.append(val)

        # last
        val = float(ticker['last'])
        if val < average:
            val = -val
        val = val / average
        states.append(val)

        # bid
        val = float(ticker['bid'])
        if val < average:
            val = -val
        val = val / average
        states.append(val)

        # ask
        val = float(ticker['ask'])
        if val < average:
            val = -val
        val = val / average
        states.append(val)

        # high
        val = float(ticker['high'])
        if val < average:
            val = -val
        val = val / average
        states.append(val)

        # low 
        val = float(ticker['low'])
        if val < average:
            val = -val
        val = val / average
        states.append(val)

        # volume
        volume = float(ticker['volume'])
        volume7 = float(ticker['volume7'])
        val = volume / volume7
        states.append(val)

        ## orderbook
        # basis = average
        basis = last
        bids = orderbook['bids']
        for bid in bids:
            q = float(bid['quantity'])
            p = float(bid['price'])
            if p < basis:
                p = -p
            p = p / basis 
            q = q * p
            states.append(q)

        asks = orderbook['asks']
        for ask in asks:
            q = float(ask['quantity'])
            p = float(ask['price'])
            if p < basis:
                p = -p
            p = p / basis 
            q = q * p
            states.append(q)

        ## recent
        #  for recent in recents:
        #      t = recent['type'].strip()
        #      u = float(recent['units_traded'])
        #      if t == 'ask':
        #          u = -u
        #      states.append(u)

        # average_cont
        if self.average_cost > 0:
            val = self.average_cost
            val = val - last
            states.append(val)
        else:
            states.append(0)

        states = np.array(states)
        return last, states


if __name__ == "__main__":
    env = Env(5000*10000)
    current_price, states = env.get_states()
    print(current_price)
    print(states)
