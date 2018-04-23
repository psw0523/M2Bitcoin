import time
import numpy as np
#  from exchange import Exchange
from bithumb import BithumbExchange
from enum import Enum


class Action(Enum):
    DO_NOTHING = 0
    BUY = 1
    SELL = 2


class Env():
    def __init__(self, initial_investment, onetime_trade_percent=0.05):
        self.exchange = BithumbExchange()
        self.currency = "BTC"
        self.average_cost = 0.0
        self.retention_amount = 0
        self.data_count = 20
        current_price, states = self.get_states()
        self.current_price = current_price
        self.states_size = len(states)
        print("states_size -> ", self.states_size)
        self.initial_investment = initial_investment
        self.onetime_trade_amount = \
                self.initial_investment * onetime_trade_percent
        self.investment = 0.0
        self.remainder = initial_investment
        self.fee_payment = 0.0
        self.fee_percent = self.exchange.get_fee()
        self.buy_count = 0.0

    def reset(self):
        """
        return state(object)
        """
        self.current_price, states = self.get_states()
        return states

    def buy(self):
        buy_count = 0.0
        buy_price = 0.0
        reward = 0.0

        if self.current_price > self.onetime_trade_amount:
            buy_count = self.current_price / self.onetime_trade_amount
        else:
            buy_count = self.onetime_trade_amount / self.current_price

        buy_price = buy_count * self.current_price
        fee = buy_price * self.fee_percent / 100;
        if self.remainder > (buy_price + fee):
            self.investment += buy_price
            self.fee_payment += fee
            self.remainder -= (buy_price + fee)
            total_cost = self.buy_count * self.average_cost + buy_price * buy_count
            self.buy_count += buy_count
            self.average_cost = total_cost / self.buy_count
        else:
            reward = -0.01
            
        return reward

    def sell(self):
        sell_count = self.onetime_trade_amount
        reward = 0.0

        sell_price = sell_count * self.current_price
        if self.investment >= sell_price:
            self.investment -= sell_price
            self.buy_count -= sell_count
            self.remainder += sell_count
            if self.current_price > self.average_cost:
                profit = sell_price - self.average_cost * self.onetime_trade_amount
                profit /= self.initial_investment
                reward = profit

        return reward

    def step(self, action):
        """
        return state(object), reward(float), done(bool), info(dict)
        """
        self.current_price, states = self.get_states()
        reward = 0.0
        done = False
        info = {}

        if action is Action.DO_NOTHING:
            if self.retention_amount > 0:
                if self.current_price < self.average_cost:
                    reward = -0.0001
            elif self.retention_amount == 0:
                reward = -0.00001
        elif action is Action.BUY:
            if self.remainder == 0:
                if self.current_price < self.average_cost:
                    reward = -0.0001
            else:
                reward = self.buy()
        elif action is Action.SELL:
            if self.investment > 0:
                reward = self.sell()

        return states, reward, done, info

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

        states = np.array(states)
        return last, states


if __name__ == "__main__":
    env = Env(5000*10000)
    current_price, states = env.get_states()
    print(current_price)
    print(states)
