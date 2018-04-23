from keras.layers import Dense, Flatten, Input
from keras.optimizers import RMSprop
from keras import backend as K
from keras.models import Model
from environment import Env
import tensorflow as tf
import numpy as np
import threading
import random
import time

# global variables for multi-threading
global episode
episode = 0
EPISODES = 8000000

def build_model(state_size, action_size):
    input = Input(shape=(state_size,))
    d = Dense(24, activation='relu')(input)
    d = Dense(24, activation='relu')(d)

    policy = Dense(action_size, activation='softmax')(d)
    value = Dense(1, activation='linear')(d)

    actor = Model(inputs=input, outputs=policy)
    critic = Model(inputs=input, outputs=value)

    actor._make_predict_function()
    critic._make_predict_function()

    actor.summary()
    critic.summary()

    return actor, critic


class A3CAgent:
    def __init__(self, env):
        self.state_size = env.state_size()
        self.action_size = env.action_size()
        # hyperparameters for A3C
        self.discount_factor = 0.99
        self.no_op_steps = 30
        self.actor_lr = 2.5e-4
        self.critic_lr = 2.5e-4
        self.threads = 8
        self.env = env

        # create policy network and value network
        self.actor, self.critic = build_model(self.state_size, self.action_size)
        # create update function
        self.optimizer = [self.actor_optimizer(), self.critic_optimizer()]

        # config tensorboard
        self.sess = tf.InteractiveSession()
        K.set_session(self.sess)
        self.sess.run(tf.global_variables_initializer())

        self.summary_placeholders, self.update_ops, self.summary_op = \
                self.setup_summary()
        self.summary_writer = \
                tf.summary.FileWriter('summary/m2bitcoin_a3c', self.sess.graph)

    def train(self):
        agents = [Agent(self.env,
                        [self.actor, self.critic],
                        self.sess, self.optimizer, self.discount_factor,
                        [self.summary_op, self.summary_placeholders, self.update_ops, self.summary_writer])
                        for _ in range(self.threads)]

        for agent in agents:
            time.sleep(1)
            agent.start()

        while True:
            time.sleep(60 * 10)
            self.save_model("./save_model/m2bitcoin_a3c")

    def actor_optimizer(self):
        action = K.placeholder(shape=[None, self.action_size])
        advantages = K.placeholder(shape=[None, ])

        policy = self.actor.output

        # cross entropy loss function
        action_prob = K.sum(action * policy, axis=1)
        cross_entropy = K.log(action_prob + 1e-10) * advantages
        cross_entropy = -K.sum(cross_entropy)

        # entropy loss for exploration
        entropy = K.sum(policy * K.log(policy + 1e-10), axis=1)
        entropy = K.sum(entropy)

        loss = cross_entropy + 0.01 * entropy

        optimizer = RMSprop(lr=self.actor_lr, rho=0.99, epsilon=0.01)
        updates = optimizer.get_updates(self.actor.trainable_weights, [], loss)
        train = K.function([self.actor.input, action, advantages], [loss],
                updates=updates)
        return train

    def critic_optimizer(self):
        discounted_prediction = K.placeholder(shape=(None,))

        value = self.critic.output

        loss = K.mean(K.square(discounted_prediction - value))

        optimizer = RMSprop(lr=self.critic_lr, rho=0.99, epsilon=0.01)
        updates = optimizer.get_updates(self.critic.trainable_weights, [], loss)
        train = K.function([self.critic.input, discounted_prediction], [loss],
                updates=updates)
        return train

    def setup_summary(self):
        episode_total_reward = tf.Variable(0.)
        episode_avg_max_q = tf.Variable(0.)
        episode_duration = tf.Variable(0.)

        tf.summary.scalar('Total Reward/Episode', episode_total_reward)
        tf.summary.scalar('Average Max Prob/Episode', episode_avg_max_q)
        tf.summary.scalar('Duration/Episode', episode_duration)

        summary_vars = [episode_total_reward, episode_avg_max_q,
                episode_duration]

        summary_placeholders = [tf.placeholder(tf.float32) for _ in
                range(len(summary_vars))]
        update_ops = [summary_vars[i].assign(summary_placeholders[i]) for i in
                range(len(summary_vars))]
        summary_op = tf.summary.merge_all()
        return summary_placeholders, update_ops, summary_op

    def save_model(self, name):
        self.actor.save_weights(name + "_actor.h5")
        self.critic.save_weights(name + "_critic.h5")

    def load_model(self, name):
        self.actor.load_weights(name + "_actor.h5")
        self.critic.load_weights(name + "_critic.h5")


# actor learner(thread)
class Agent(threading.Thread):
    def __init__(self, env, model, sess, optimizer,
            discount_factor, summary_ops):
        threading.Thread.__init__(self)

        self.env = env
        self.state_size = env.state_size()
        self.action_size = env.action_size()
        self.actor, self.critic = model
        self.sess = sess
        self.optimizer = optimizer
        self.discount_factor = discount_factor
        [self.summary_op, self.summary_placeholders, self.update_ops,
                self.summary_writer] = summary_ops

        self.states, self.actions, self.rewards = [], [], []

        self.local_actor, self.local_critic = build_model(self.state_size,
                self.action_size)

        self.avg_p_max = 0
        self.avg_loss = 0

        # cycle to update model
        self.t_max = 20
        self.t = 0

    def run(self):
        global episode
        env = self.env

        step = 0

        while episode < EPISODES:
            done = False
            score = 0

            state = env.reset()

            while not done:
                step += 1
                self.t += 1
                action, policy = self.get_action(state)
                print("action -> ", action)
                print("policy -> ", policy)

                next_state, reward, done, info = env.step(action)

                self.avg_p_max += np.amax(self.actor.predict(next_state.reshape((1, self.state_size))))

                score += reward
                reward = np.clip(reward, -1., 1.)
                
                self.append_sample(state, action, reward)

                state = next_state

                if self.t >= self.t_max or done:
                    self.train_model(done)
                    self.update_local_model()
                    self.t = 0

                if done:
                    episode += 1
                    print("episode:", episode, " score:", score, " step:", step)

                    stats = [score, self.avg_p_max / float(step), step]
                    for i in range(len(stats)):
                        self.sess.run(self.update_ops[i], feed_dict={
                            self.summary_placeholders[i]: float(stats[i])
                        })
                    summary_str = self.sess.run(self.summary_op)
                    self.summary_writer.add_summary(summary_str, episode + 1)
                    self.avg_p_max = 0
                    self.avg_loss = 0
                    step = 0

    # calculate n-step prediction
    def discounted_prediction(self, rewards, done):
        discounted_prediction = np.zeros_like(rewards)
        running_add = 0

        if not done:
            running_add = self.critic.predict(self.states[-1])[0]

        for t in reversed(range(0, len(rewards))):
            running_add = running_add * self.discount_factor + rewards[t]
            discounted_prediction[t] = running_add
        
        return discounted_prediction

    # update actor,critic neural network
    def train_model(self, done):
        discounted_prediction = self.discounted_prediction(self.rewards, done)

        states = np.zeros(len(self.states))
        for i in range(len(self.states)):
            states[i] = self.states[i]

        values = self.critic.predict(states)
        values = np.reshape(values, len(values))

        advantages = discounted_prediction - values

        self.optimizer[0]([states, self.actions, advantages])
        self.optimizer[1]([states, discounted_prediction])
        self.states, self.actions, self.rewards = [], [], []

    # update local network by global network
    def update_local_model(self):
        self.local_actor.set_weights(self.actor.get_weights())
        self.local_critic.set_weights(self.critic.get_weights())

    def get_action(self, state):
        policy = self.local_actor.predict(state.reshape(1, self.state_size))[0]
        action_index = np.random.choice(self.action_size, 1, p=policy)[0]
        return action_index, policy

    def append_sample(self, state, action, reward):
        self.states.append(state)
        act = np.zeros(self.action_size)
        act[action] = 1
        self.actions.append(act)
        self.rewards.append(reward)


if __name__ == "__main__":
    global_agent = A3CAgent(Env(5000*10000))
    global_agent.train()
