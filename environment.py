import time
import numpy as np

class Env():
    def __init__(self):
        pass

    def reset(self):
        """
        return state(object)
        """
        pass

    def step(self, action):
        """
        return state(object), reward(float), done(bool), info(dict)
        """
        pass

    def state_size(self):
        pass

    def action_size(self):
        pass
