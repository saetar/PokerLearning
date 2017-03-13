import random
from util import Counter
from util import Actions
from util import PreflopEvaluator
import pickle

class Player:
    def __init__(self, chips):
        self.hand = []
        self.chips = chips
        self.winnings = 0
        self.stats = Counter()
        self.actions = []
        self.hand_features = []  # holds list of (game_state,action) pairs for training once we know whether we won or not
        self.learning_rate = 0.5

    def add_card_to_hand(self, card):
        self.hand.append(card)

    def reset_chips(self, chip_amount):
        self.chips = chip_amount

    def get_hand(self):
        return self.hand

    def is_out(self):
        return self.chips <= 0

    def ante(self, value):
        self.chips -= value
        return value

    def won(self, total_chips, pool_amt): #fuck this hsit
        this_winnings = self.chips - total_chips + pool_amt
        self.winnings += this_winnings

    def loss(self, total_chips, pool_amt):
        this_winnings = self.chips - total_chips
        self.winnings += this_winnings

    def clear_hand(self):
        self.hand = []

    def get_stats(self):
        if len(self.actions) > 0:
            self.stats['raise-rate'] = sum([action == Actions.RAISE for action in self.actions]) / len(self.actions)
            self.stats['fold-rate'] = sum(action == Actions.FOLD for action in self.actions) / len(self.actions)
            self.stats['call-rate'] = sum(action == Actions.CALL for action in self.actions) / len(self.actions)
        return self.stats

    def get_legal_actions(self, game_state, bid_amount, raise_amount):
        if self.chips == 0:
            return [Actions.FOLD, Actions.CALL]
        else:
            return Actions

    @staticmethod
    def print_communal_cards(communal_cards):
        commuanl_cards_strs = " " * 20 + "*" * 19 + "\n"
        commuanl_cards_strs += " " * 20
        commuanl_cards_strs += "  ".join(["{}".format(card.to_str()) for card in communal_cards])
        commuanl_cards_strs += "\n" + " " * 20 + "*" * 19 + "\n"
        print("\n{}\n".format(commuanl_cards_strs))

    def get_bid(self, game_state, bid_amount, raise_amount):
        return None

    def print_hand(self):
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        print(hcs)

class QLearningPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)
        self.q_learning_weights = self.load_q_learning_weights()

    def get_computer_bid(self, game_state, bid_amount, raise_amount):
        print(game_state)
        action = self.get_q_star_action(game_state, bid_amount, raise_amount)
        self.actions.append(action)
        return action

    def make_q_learning_dict_from_state(self, game_state):
        q_learning_dict = Counter()
        for key, value in game_state.items():
            if type(value) in [int, bool, float]:
                q_learning_dict[key] = value
            elif key == "communal-cards":
                if len(value) == 0: # use preflop evaluator
                    preflop_scores = PreflopEvaluator.evaluate_cards(self.hand)
                    for key2, value2 in preflop_scores.items():
                        q_learning_dict["hand-{}".format(key2)] = value2
        return q_learning_dict

    def won(self, total_chips, pool_amt): #fuck this hsit
        this_winnings = self.chips - total_chips + pool_amt
        self.winnings += this_winnings
        self.update_weights(this_winnings)

    def loss(self, total_chips, pool_amt):
        this_winnings = self.chips - total_chips
        self.winnings += this_winnings
        self.update_weights(this_winnings)

    def get_q_value(self, game_state, action):
        q_learning_dict = self.make_q_learning_dict_from_state(game_state)
        score = 0.0
        for key in q_learning_dict:
            score += q_learning_dict[key] * self.q_learning_weights[key]
        return score

    def get_legal_actions(self, game_state, bid_amount, raise_amount):
        if self.chips == 0:
            return [Actions.FOLD, Actions.CALL]
        else:
            return Actions

    def get_q_star_action(self, game_state, bid_amount, raise_amount):
        optimal_action = []
        max_score = float("-inf")
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        for action in actions:
            score = self.get_q_value(game_state, action)
            if score > max_score:
                optimal_action = [action]
                max_score = score
            elif score == max_score:
                optimal_action.append(action)
        return random.choice(optimal_action)

    def update_weights(self, winnings):
        weights = self.q_learning_weights
        """  gotta train them weights  """
        for state, action in self.hand_features:
            difference = winnings - self.get_q_value(state, action)
            q_learning_dict = self.make_q_learning_dict_from_state(state)
            for feature in q_learning_dict:
                weights[feature] += self.learning_rate * difference * q_learning_dict[feature]
        self.hand_features = []

    def get_bid(self, game_state, bid_amount, raise_amount):
        return self.get_q_star_action(game_state, bid_amount, raise_amount)

    def load_q_learning_weights(self):
        try:
            weights = pickle.load(open("learning_data/q_learning_weights.p", "rb"))
        except:
            weights = Counter()
        return weights

    def store_q_learning_weights(self):
        weights = self.q_learning_weights
        pickle.dump(weights, open("learning_data/q_learning_weights.p", "wb"))


class HumanPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)

    def get_human_bid(self, game_state):
        print(game_state)
        communal_cards = game_state['communal-cards']
        action = None
        Player.print_communal_cards(communal_cards)
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        print("Your hand is {}".format(hcs))
        bid = input("Would you like to [f]old, [c]all, or [r]aise?\n")
        if bid[0] == 'f':
            action = Actions.FOLD
        elif bid[0] == 'c':
            action = Actions.CALL
        else:
            action = Actions.RAISE
        self.actions.append(action)
        return action

    def get_bid(self, game_state, bid_amount, raise_amount):
        return self.get_human_bid(game_state)


class RandomPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)

    def get_bid(self, game_state, bid_amount, raise_amount):
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        return random.choice(actions)