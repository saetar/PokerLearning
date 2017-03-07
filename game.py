import itertools
from enum import Enum
from player import Player
from deck import Deck


class Actions(Enum):
    FOLD = 0
    CALL = 1
    RAISE = 2


class Game:
    def __init__(self, chips):
        self.human_player = Player(chips, False)
        self.computer_player = Player(chips, True)
        self.deck = Deck()

    @staticmethod
    def get_actions():
        return Actions

    def start_game(self):
        """
            While there are chips in either players pockets, play hands
        """
        bid_amount = 5
        counter = -1
        while not self.human_player.is_out() and not self.computer_player.is_out():
            first_player = self.computer_player if counter < 0 else self.human_player
            second_player = self.human_player if counter < 0 else self.computer_player
            self.play_hand(first_player, second_player, bid_amount)
            counter *= -1

    def play_hand(self, first_player, second_player, bid_amount):
        """
            plays out a hand, keeping track of antes, and actions
        """
        self.deck.shuffle()
        communal_cards = set()
        winner = None
        first_player.clear_hand()
        second_player.clear_hand()
        """  Deal initial hands to players  """
        first_player.add_card_to_hand(self.deck.pop())
        second_player.add_card_to_hand(self.deck.pop())
        first_player.add_card_to_hand(self.deck.pop())
        second_player.add_card_to_hand(self.deck.pop())

        """  initialize pool and ante up players  """
        pool = 0
        pool += first_player.ante(bid_amount / 2.0)
        pool += second_player.ante(bid_amount)

        """  Go through a round of betting  """
        pool_amt, winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        pool += pool_amt
        if winner is not None:
            winner.won(pool)
            return

        """  Add 3 cards to communal cards, with burns  """
        self.deck.pop()
        communal_cards.add(self.deck.pop())
        self.deck.pop()
        communal_cards.add(self.deck.pop())
        self.deck.pop()
        communal_cards.add(self.deck.pop())

        """  Go through a 2nd round of betting  """
        pool_amt, winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        pool += pool_amt
        if winner:
            winner.won(pool)
            return

        """  Add one card to communal with burn  """
        self.deck.pop()
        communal_cards.add(self.deck.pop())

        """  Go through a 3nd round of betting  """
        pool_amt, winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        pool += pool_amt
        if winner:
            winner.won(pool)
            return

        """  Add one card to communal with burn  """
        self.deck.pop()
        communal_cards.add(self.deck.pop())

        """  Go through a 3nd round of betting  """
        pool_amt, winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        pool += pool_amt
        if winner:
            winner.won(pool)
            return

        """  Evaluate hands at end  """
        first_player_cards = Hand(communal_cards.union(first_player.get_hand()))
        second_player_cards = Hand(communal_cards.union(second_player.get_hand()))
        if first_player_cards < second_player_cards:
            second_player.won(pool)
        elif first_player > second_player_cards:
            first_player.won(pool)
        else:
            first_player.won(pool / 2.0)
            second_player.won(pool / 2.0)

    def do_betting_round(self, first_player, second_player, bid_amount, communal_cards):
        """
        :param first_player: first player in rotation
        :param second_player: second player in rotation
        :param bid_amount: amount each bid is worth
        :param communal_cards: communal cards
        :return (pool, winner)
                 pool is total amount bet, winner is player that won else None:
        """
        pool = 0
        do_again = True
        winner = None
        while do_again:
            first_player_bet, second_player_bet = self.get_bids(first_player, second_player, communal_cards)
            if first_player_bet == Actions.RAISE:
                pool += first_player.ante(bid_amount)
                if second_player_bet == Actions.CALL:
                    pool += second_player.ante(bid_amount)
                    do_again = False
                elif second_player_bet == Actions.FOLD:
                    winner = first_player
                    do_again = False
                elif second_player_bet == Actions.RAISE:
                    pool += second_player.ante(2 * bid_amount)
                    do_again = True
            elif first_player_bet == Actions.CALL:
                if second_player_bet == Actions.RAISE:
                    pool += second_player.ante(bid_amount)
                    do_again = True
                elif second_player_bet == Actions.CALL:
                    if do_again:
                        pool += first_player.ante(bid_amount)
                    do_again = False
                elif second_player_bet == Actions.FOLD:
                    winner = first_player
                    do_again = False
            elif first_player_bet == Actions.FOLD:
                winner = second_player
                do_again = False
        return pool, winner

    @staticmethod
    def get_bids(first_player, second_player, communal_cards):
        first_player_game_state = (Actions, communal_cards, second_player)
        first_player_bet = first_player.get_bid(first_player_game_state)
        second_player_game_state = (Actions, communal_cards, first_player)
        second_player_bet = second_player.get_bid(second_player_game_state, other_bet=first_player_bet)
        return first_player_bet, second_player_bet


class HandType(Enum):
    NONE = 0
    PAIR = 1
    TWO_PAIR = 2
    THREES = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOURS = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


class Hand:
    def __init__(self, cards):
        self.cards = cards

    def get_hand_type(self):
        if len(self.cards) == 5:
            five_cards = itertools.permutations(self.cards, 5)
            hands = [Hand(cards) for cards in five_cards]
            best_hand_amt = float('-inf')
            for hand in hands:
                hand_type = hand.get_hand_type()
                if hand_type > best_hand_amt:
                    best_hand_amt = hand_type

    # def __lt__(self, other):


def main():
    game = Game(100)
    game.start_game()

if __name__ == '__main__':
    main()
