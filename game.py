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
        self.pool = 0
        print("You start with:", chips, "chips")

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
            print("-------------- NEW HAND -------------")
            counter *= -1

    def play_hand(self, first_player, second_player, bid_amount):
        """
            :param first_player: first player to bid
            :param second_player: the second player to bid
            :param bid_amount: the amount a raise is worth

            plays out a hand, keeping track of antes, and actions
        """
        """ Tell the player how many chips they have and which player they are"""
        print("You have", self.human_player.chips, "chips")
        if self.human_player == first_player:
            print("You are the first player")
            opponent_player = second_player
        elif self.human_player == second_player:
            print("You are the second player")
            opponent_player = first_player
        else:
            print("rip")
            
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
        self.pool = 0
        self.pool += first_player.ante(bid_amount / 2.0)
        self.pool += second_player.ante(bid_amount)
        print("The pot starts at: ", self.pool)
        """  Go through a round of betting  """
        winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        print("The pot preflop is: ", self.pool)
        if winner is not None:
            winner.won(self.pool)
            return

        """  Add 3 cards to communal cards, with burns  """
        self.deck.pop()
        communal_cards.add(self.deck.pop())
        self.deck.pop()
        communal_cards.add(self.deck.pop())
        self.deck.pop()
        communal_cards.add(self.deck.pop())

        """  Go through a 2nd round of betting  """
        winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        print("The pot after the flop is: ", self.pool)
        if winner:
            winner.won(self.pool)
            return

        """  Add one card to communal with burn  """
        self.deck.pop()
        communal_cards.add(self.deck.pop())

        """  Go through a 3nd round of betting  """
        winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        print("The pot after the turn is: ", self.pool)
        if winner:
            winner.won(self.pool)
            return

        """  Add one card to communal with burn  """
        self.deck.pop()
        communal_cards.add(self.deck.pop())

        """  Go through a 3nd round of betting  """
        winner = self.do_betting_round(first_player, second_player, bid_amount, communal_cards)
        print("The pot after the river is: ", self.pool)
        if winner:
            winner.won(self.pool)
            return

        """  Evaluate hands at end  """
        first_player_cards = Hand(communal_cards.union(first_player.get_hand()))
        second_player_cards = Hand(communal_cards.union(second_player.get_hand()))
        if first_player_cards < second_player_cards:
            second_player.won(self.pool)
        elif first_player > second_player_cards:
            first_player.won(self.pool)
        else:
            first_player.won(self.pool / 2.0)
            second_player.won(self.pool / 2.0)

    def do_betting_round(self, first_player, second_player, bid_amount, communal_cards):
        """
        :param first_player: first player in rotation
        :param second_player: second player in rotation
        :param bid_amount: amount each bid is worth
        :param communal_cards: communal cards
        :return (pool, winner)
                 pool is total amount bet, winner is player that won else None:
        """
        #pool = 0 #We don't want to reset the pool to 0
        do_again = True
        winner = None
        no_bets = True
        second_player_bet = -1
        while do_again:
            first_player_bet = self.get_bid(first_player, second_player, communal_cards, second_player_bet)
            if first_player_bet == Actions.RAISE:
                no_bets = False
                self.pool += first_player.ante(bid_amount)
                print("first player raised: ",bid_amount,"\n")
                second_player_bet = self.get_bid(second_player, first_player, communal_cards, first_player_bet)
                if second_player_bet == Actions.CALL:
                    self.pool += second_player.ante(bid_amount)
                    print("second player called the raise\n")
                    do_again = False
                elif second_player_bet == Actions.FOLD:
                    winner = first_player
                    print("second player folded\n")
                    do_again = False
                elif second_player_bet == Actions.RAISE:
                    print("second player raised\n")
                    self.pool += second_player.ante(2 * bid_amount)
                    do_again = True
            elif first_player_bet == Actions.CALL:
                if no_bets:
                    print("first player checked\n")
                    second_player_bet = self.get_bid(second_player, first_player, communal_cards,first_player_bet)
                    if second_player_bet == Actions.RAISE:
                        no_bets = False
                        print("second player raised\n")
                        self.pool += second_player.ante(bid_amount)
                        do_again = True
                    elif second_player_bet == Actions.CALL:
                        if no_bets:
                            print("second player checked\n")
                        else:        
                            print("second player called\n")
                        if not no_bets:
                            self.pool += first_player.ante(bid_amount)
                        do_again = False
                    elif second_player_bet == Actions.FOLD:
                        print("second player folded\n")
                        winner = first_player
                        do_again = False
                else:
                    print("first player called\n")
                    do_again = False
                
            elif first_player_bet == Actions.FOLD:
                print("first player folded\n")
                winner = second_player
                do_again = False
        
        return winner

    @staticmethod
    def get_bids(first_player, second_player, communal_cards):
        first_player_game_state = (Actions, communal_cards, second_player)
        first_player_bet = first_player.get_bid(first_player_game_state)
        second_player_game_state = (Actions, communal_cards, first_player)
        second_player_bet = second_player.get_bid(second_player_game_state, other_bet=first_player_bet)
        return first_player_bet, second_player_bet

    #We need to get the bids 1 at a time
    @staticmethod
    def get_bid(player, opponent, communal_cards, opponent_bet):
        player_game_state = (Actions, communal_cards, opponent_bet, opponent)
        player_bet = player.get_bid(player_game_state)
        return player_bet


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
