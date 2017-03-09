import random
from util import Counter
from util import Actions
from util import PreflopEvaluator
import pickle

class Player:
    def __init__(self, chips, is_computer):
        self.hand = []
        self.chips = chips
        self.is_computer = is_computer
        self.winnings = 0
        self.stats = Counter()
        self.actions = []
        self.q_learning_weights = self.load_q_learning_weights()

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
        self.winnings += self.chips - total_chips + pool_amt

    def loss(self, total_chips, pool_amt):
        self.winnings += self.chips - total_chips

    def clear_hand(self):
        self.hand = []

    def get_stats(self):
        if len(self.actions) > 0:
            self.stats['raise-rate'] = sum([action == Actions.RAISE for action in self.actions]) / len(self.actions)
            self.stats['fold-rate'] = sum(action == Actions.FOLD for action in self.actions) / len(self.actions)
            self.stats['call-rate'] = sum(action == Actions.CALL for action in self.actions) / len(self.actions)
        return self.stats

    def make_q_learning_dict_from_state(self, game_state):
        q_learning_dict = Counter()
        for key, value in game_state.items():
            if type(value) in [int, bool, float]:
                q_learning_dict[key] = value
            elif key == "communal-cards":
                if len(value) == 0: # use preflop evaluator
                    preflop_scores = PreflopEvaluator.evaluate_cards(self.hand)
                    for key, value in preflop_scores.items():
                        q_learning_dict["hand-{}".format(key)] = value
        return q_learning_dict

    @staticmethod
    def print_communal_cards(communal_cards):
        commuanl_cards_strs = " " * 20 + "*" * 19 + "\n"
        commuanl_cards_strs += " " * 20
        commuanl_cards_strs += "  ".join(["{}".format(card.to_str()) for card in communal_cards])
        commuanl_cards_strs += "\n" + " " * 20 + "*" * 19 + "\n"
        print("\n{}\n".format(commuanl_cards_strs))

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

    def get_computer_bid(self, game_state):
        q_learning_dict = self.make_q_learning_dict_from_state(game_state)
        print("QLEARNING: {}".format(q_learning_dict))
        communal_cards = game_state['communal-cards']
        other_player_action = None
        if game_state['no-bets'] is False:
            other_player_action = Actions.RAISE
        elif game_state['first-player'] != self:
            other_player_action = Actions.CALL
        # Random action for now
        # If they raised or we are preflop and they didn't check to us in the big blind we can fold.
        # Otherwise we should never fold because we don't have to put in more chips
        if (other_player_action == Actions.RAISE) or (other_player_action != Actions.CALL and not communal_cards):
            action_choices = [Actions.RAISE, Actions.CALL, Actions.FOLD]
            action = random.choice(action_choices)
        else:
            action_choices = [Actions.RAISE, Actions.CALL]
            action = random.choice(action_choices)
        self.actions.append(action)
        return action

    def get_bid(self, game_state):
        if self.is_computer:
            return self.get_computer_bid(game_state)
        else:
            return self.get_human_bid(game_state)

    def print_hand(self):
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        print(hcs)

    def load_q_learning_weights(self):
        try:
            weights = pickle.load(open("q_learning_weights.p", "rb"))
        except:
            weights = Counter()
        return weights

    def store_q_learning_weights(self):
        weights = self.q_learning_weights
        pickle.dump(weights, open("q_learning_weights.p", "wb"))
