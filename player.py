import random
from game import Actions

class Player:
    def __init__(self, chips, is_computer):
        self.hand = set()
        self.chips = chips
        self.is_computer = is_computer

    def add_card_to_hand(self, card):
        self.hand.add(card)

    def get_hand(self):
        return self.hand

    def is_out(self):
        return self.chips <= 0

    def ante(self, value):
        self.chips -= value
        return value

    def won(self, pool_amt):
        self.chips += pool_amt

    def get_bid(self, game, bid_amount):
        if not self.is_computer:
            bid = input()
            if bid[0] == 'f':
                return Actions.FOLD
            if bid[0] == 'c':
                return Actions.CALL
            return Actions.RAISE
        else: # Random action for now
            actions = [Actions.RAISE, Actions.CALL, Actions.FOLD]
            action = random.choice(actions)
            return action