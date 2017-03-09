import random
from util import Counter
from util import Actions

class Player:
    def __init__(self, chips, is_computer):
        self.hand = []
        self.chips = chips
        self.is_computer = is_computer
        self.winnings = 0
        self.stats = Counter()
        self.actions = []

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
        return self.stats

    def get_bid(self, game_state):
        communal_cards = game_state['communal-cards']
        other_player_action = None
        if game_state['no-bets'] is False:
            other_player_action = Actions.RAISE
        elif game_state['first-player'] != self:
            other_player_action = Actions.CALL
        action = None
        if not self.is_computer:
            commuanl_cards_strs = " " * 20 + "*" * 19 + "\n"
            commuanl_cards_strs += " " * 20
            commuanl_cards_strs += "  ".join(["{}".format(card.to_str()) for card in communal_cards])
            commuanl_cards_strs += "\n" + " " * 20 + "*" * 19 + "\n"
            hand_cards_str = [card.to_str() for card in self.hand]
            hcs = ", ".join(hand_cards_str)
            print("\n{}\nYour hand is {}".format(commuanl_cards_strs, hcs))
            bid = input("Would you like to [f]old, [c]all, or [r]aise?\n")
            if bid[0] == 'f':
                action = Actions.FOLD
            elif bid[0] == 'c':
                action = Actions.CALL
            else:
                action = Actions.RAISE
        else:
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

    def print_hand(self):
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        print(hcs)
