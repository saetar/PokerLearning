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

    def get_bid(self, game_state):
        (actions, communal_cards, other_player_action, other_player_stats, bidding_round) = game_state
        if not self.is_computer:
            communal_cards_strs = [card.to_str() for card in communal_cards]
            ccs = ", ".join(communal_cards_strs)
            hand_cards_str = [card.to_str() for card in self.hand]
            hcs = ", ".join(hand_cards_str)
            print("\nThe communal cards are: {}, and your hand is {}".format(ccs, hcs))
            bid = input("Would you like to [f]old, [c]all, or [r]aise?\n")
            if bid[0] == 'f':
                return actions.FOLD
            if bid[0] == 'c':
                return actions.CALL
            return actions.RAISE
        else:
            # Random action for now
            # If they raised or we are preflop and they didn't check to us in the big blind we can fold.
            # Otherwise we should never fold because we don't have to put in more chips
            if (other_player_action == 2) or (not other_player_action == 1 and not communal_cards):
                action_choices = [actions.RAISE, actions.CALL, actions.FOLD]
                action = random.choice(action_choices)
            else:
                action_choices = [actions.RAISE, actions.CALL]
                action = random.choice(action_choices)
            return action

    def print_hand(self):
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        print(hcs)