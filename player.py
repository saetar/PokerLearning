import random


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

    def clear_hand(self):
        self.hand = set()

    def get_bid(self, game_state, other_bet=None):
        (actions, communal_cards, other_player_action, other_player_stats) = game_state
        if other_bet is not None:
            print(other_bet)
        if not self.is_computer:
            communal_cards_strs = [str(card) for card in communal_cards]
            ccs = ", ".join(communal_cards_strs)
            hand_cards_str = [str(card) for card in self.hand]
            hcs = ", ".join(hand_cards_str)
            print("The communal cards are: {}, and your hand is {}".format(ccs, hcs))
            bid = input("Would you like to [f]old, [c]all, or [r]aise?")
            if bid[0] == 'f':
                return actions.FOLD
            if bid[0] == 'c':
                return actions.CALL
            return actions.RAISE
        else:  # Random action for now
            if(other_player_action == 2 or not communal_cards):
                action_choices = [actions.RAISE, actions.CALL, actions.FOLD]
                action = random.choice(action_choices)
            else:
                action_choices = [actions.RAISE, actions.CALL]
                action = random.choice(action_choices)
                
            return action
