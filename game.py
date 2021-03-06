from util import Actions
from player import HumanPlayer, QLearningPlayer, RandomPlayer, TightPlayer, AggressivePlayer
from deck import Deck
from deuces import Card
from deuces import Evaluator
from util import Counter
from util import BiddingRound
import sys

class Game:
    def __init__(self, chips, opponent):
        self.q_learning_player = QLearningPlayer(chips, opponent)
        self.opponent_player = opponent(chips)
        self.deck = Deck()
        self.pool = 0
        self.chips = chips
        self.hands_played = 0
        self.game_state = Counter()
        self.game_state["player-1"] = self.q_learning_player
        self.game_state["player-2"] = self.opponent_player
        self.all_in = False

    @staticmethod
    def get_actions():
        return Actions

    def start_game(self, num_hands):
        """
            While there are chips in either players pockets, play hands
        """
        bid_amount = 5
        counter = -1
        for i in range(num_hands):
            if i%100 == 0:
                print("another 100 hands")
            first_player = self.opponent_player if counter < 0 else self.q_learning_player
            second_player = self.q_learning_player if counter < 0 else self.opponent_player
            self.play_hand(first_player, second_player, bid_amount)
            if type(first_player) == QLearningPlayer:
                first_player.store_q_learning_weights()
            if type(second_player) == QLearningPlayer:
                second_player.store_q_learning_weights()
            self.hands_played += 1
            self.get_players_winnings()
            ##print("-------------- NEW HAND -------------")
            counter *= -1
        print("computer player winnings")
        print(self.opponent_player.first_half_winnings, self.opponent_player.last_half_winnings)
        print("human player winnings")
        print(self.q_learning_player.first_half_winnings, self.q_learning_player.last_half_winnings)

    def play_hand(self, first_player, second_player, bid_amount):
        """
            :param first_player: first player to bid
            :param second_player: the second player to bid
            :param bid_amount: the amount a raise is worth

            plays out a hand, keeping track of antes, and actions
        """
        """ Tell the player how many chips they have and which player they are"""
        if self.q_learning_player == first_player:
            ##print("You are the first player")
            opponent_player = second_player
        elif self.q_learning_player == second_player:
            ##print("You are the second player")
            opponent_player = first_player
        self.deck = Deck()
        self.deck.shuffle()
        communal_cards = []
        winner = None
        first_player.clear_hand()
        second_player.clear_hand()
        """  Deal initial hands to players  """
        first_player.add_card_to_hand(self.deck.pop())
        second_player.add_card_to_hand(self.deck.pop())
        first_player.add_card_to_hand(self.deck.pop())
        second_player.add_card_to_hand(self.deck.pop())
        """  initialize player chip amount  """
        first_player.reset_chips(self.chips)
        second_player.reset_chips(self.chips)
        self.all_in = False
        """  initialize pool and ante up players  """
        self.pool = 0
        self.pool += first_player.ante(bid_amount / 2.0)
        self.pool += second_player.ante(bid_amount)
        ##print("The pot starts at: ", self.pool)
        """  Go through a round of betting  """
        winner = self.do_betting_round(first_player, second_player, communal_cards, BiddingRound.PREFLOP)
        ##print("The pot preflop is: ", self.pool)
        if winner is not None:
            loser = first_player if first_player is not winner else second_player
            winner.won(self.chips, self.pool)
            loser.loss(self.chips, self.pool)
            return
        """  Add 3 cards to communal cards, with burns  """
        self.deck.pop()
        communal_cards.append(self.deck.pop())
        self.deck.pop()
        communal_cards.append(self.deck.pop())
        self.deck.pop()
        communal_cards.append(self.deck.pop())
        if not self.all_in:
            """  Go through a 2nd round of betting if not all in  """
            winner = self.do_betting_round(first_player, second_player, communal_cards, BiddingRound.POST_FLOP)
        ##print("The pot after the flop is: ", self.pool)
        if winner:
            loser = first_player if first_player is not winner else second_player
            winner.won(self.chips, self.pool)
            loser.loss(self.chips, self.pool)
            return

        """  Add one card to communal with burn  """
        self.deck.pop()
        communal_cards.append(self.deck.pop())
        if not self.all_in:
            """  Go through a 3nd round of betting  """
            winner = self.do_betting_round(first_player, second_player, communal_cards, BiddingRound.POST_FLOP)
        ##print("The pot after the turn is: ", self.pool)
        if winner:
            loser = first_player if first_player is not winner else second_player
            winner.won(self.chips, self.pool)
            loser.loss(self.chips, self.pool)
            return

        """  Add one card to communal with burn  """
        self.deck.pop()
        communal_cards.append(self.deck.pop())
        if not self.all_in:
            """  Go through a 4th round of betting  """
            winner = self.do_betting_round(first_player, second_player, communal_cards, BiddingRound.POST_FLOP)
        #print("The pot after the river is: ", self.pool)
        if winner:
            loser = first_player if first_player is not winner else second_player
            winner.won(self.chips, self.pool)
            loser.loss(self.chips, self.pool)
            return

        """  Evaluate hands at end  """
        community_cards_strs = [str(card) for card in communal_cards]
        #print("*" * 50)
        #print(", ".join(community_cards_strs))
        #print("*" * 50)
        first_player_score = self.evalHand(first_player.get_hand(), list(communal_cards))
        second_player_score = self.evalHand(second_player.get_hand(), list(communal_cards))
        # LOW SCORE WINS IN DEUCES
        if first_player_score > second_player_score:
            #print("second player won a pot of: ", self.pool)
            #print("they had")
            #second_player.print_hand()
            second_player.won(self.chips, self.pool, True)
            first_player.loss(self.chips, self.pool, True)
        elif first_player_score < second_player_score:
            #print("first player won a pot of: ", self.pool)
            #print("they had")
            #first_player.print_hand()
            first_player.won(self.chips, self.pool, True)
            second_player.loss(self.chips, self.pool, True)
        else:
            #print("split pot!")
            first_player.won(self.chips, self.pool / 2.0, True)
            second_player.won(self.chips, self.pool / 2.0, True)

    def update_game_state(self, key, value):
        self.game_state[key] = value

    def do_betting_round(self, first_player, second_player, communal_cards, bidding_round):
        """
        :param bidding_round: the round of bidding
        :param first_player: first player in rotation
        :param second_player: second player in rotation
        :param bid_amount: amount each bid is worth
        :param communal_cards: communal cards
        :return (pool, winner)
                 pool is total amount bet, winner is player that won else None:
        """
        self.update_game_state("communal-cards", communal_cards)
        first = self.opponent_player if first_player == self.opponent_player else self.q_learning_player
        self.update_game_state("first-player", first)
        self.update_game_state("betting-round", bidding_round)
        self.update_game_state("pool-amount", self.pool)
        do_again = True
        winner = None
        no_bets = True
        self.update_game_state("no-bets", no_bets)
        second_player_bet = -1
        bid_amount = max(self.pool / 2, 5)
        raise_amount = bid_amount
        while do_again and not self.all_in:
            first_player_bet = self.get_bid(first_player, second_player, communal_cards,
                                            second_player_bet, bid_amount, raise_amount)
            if first_player_bet == Actions.RAISE:
                if no_bets and self.game_state["betting-round"] == BiddingRound.PREFLOP:
                    self.pool += first_player.ante(7.5)
                    self.update_game_state("pool-amount", self.pool)
                else:
                    if raise_amount > first_player.chips:
                        self.all_in = True
                        raise_amount = first_player.chips
                        self.update_game_state("all-in", True)
                    self.pool += first_player.ante(raise_amount)
                no_bets = False

                self.update_game_state("pool-amount", self.pool)
                self.update_game_state("no-bets", no_bets)
                bid_amount = raise_amount
                raise_amount *= 2
                #print("first player raised: ", bid_amount)
                second_player_bet = self.get_bid(second_player, first_player, communal_cards, first_player_bet,
                                                 bid_amount, raise_amount)
                if second_player_bet == Actions.CALL:
                    self.pool += second_player.ante(bid_amount)
                    self.update_game_state("pool-amount", self.pool)
                    #print("second player called the raise\n")
                    do_again = False
                elif second_player_bet == Actions.FOLD:
                    winner = first_player
                    #print("second player folded\n")
                    do_again = False
                elif second_player_bet == Actions.RAISE:
                    if raise_amount > second_player.chips:
                        self.all_in = True
                        raise_amount = second_player.chips
                    self.update_game_state("all-in", self.all_in)
                    #print("second player raised\n")
                    self.pool += second_player.ante(raise_amount)
                    self.update_game_state("pool-amount", self.pool)
                    bid_amount = raise_amount
                    raise_amount *= 2
                    do_again = True
            elif first_player_bet == Actions.CALL:
                if no_bets:
                    if self.game_state["betting-round"] == BiddingRound.PREFLOP:
                        self.pool += first_player.ante(float(bid_amount / 2))
                        self.update_game_state("pool-amount", self.pool)
                    #print("first player checked\n")
                    second_player_bet = self.get_bid(second_player, first_player, communal_cards, first_player_bet,
                                                     bid_amount, raise_amount)
                    if second_player_bet == Actions.RAISE:
                        if raise_amount > second_player.chips:
                            self.all_in = True
                            raise_amount = second_player.chips
                        self.update_game_state("all-in", self.all_in)
                        no_bets = False
                        self.update_game_state("no-bets", no_bets)
                        #print("second player raised\n")
                        self.pool += second_player.ante(raise_amount)
                        self.update_game_state("pool-amount", self.pool)
                        bid_amount = raise_amount
                        raise_amount *= 2
                        do_again = True
                    elif second_player_bet == Actions.CALL:
                        if no_bets:
                            pass
                            #print("second player checked\n")
                        else:
                            pass
                            #print("second player called\n")
                        if not no_bets:
                            self.pool += second_player.ante(bid_amount)
                            self.update_game_state("pool-amount", self.pool)
                        do_again = False
                    elif second_player_bet == Actions.FOLD:
                        #print("second player folded\n")
                        winner = first_player
                        do_again = False
                else:
                    self.pool += first_player.ante(bid_amount)

                    self.update_game_state("pool-amount", self.pool)
                    #print("first player called\n")
                    do_again = False

            elif first_player_bet == Actions.FOLD:
                #print("first player folded\n")
                winner = second_player
                do_again = False
        return winner

    #We need to get the bids 1 at a time
    def get_bid(self, player, opponent, communal_cards, opponent_bet, bid_amount, raise_amount):
        self.update_game_state("pool-amount", self.pool / 1000.0)
        game_state = self.game_state.copy()
        opponent_stats = opponent.get_stats()
        for key, value in opponent_stats.items():
            game_state["opponent-{}".format(key)] = value
        player_stats = player.get_stats()
        for key, value in player_stats.items():
            game_state["player-{}".format(key)] = value
        if len(communal_cards) > 0:
            game_state["player-total-score"] = Game.evalHand(player.get_hand(), communal_cards) / 10000.0
        player_bet = player.get_bid(game_state, bid_amount, raise_amount)
        return player_bet

    @staticmethod
    def evalHand(hand, communal_cards):
        if communal_cards:
            communal_cards_strs = [str(card) for card in communal_cards]
        hand_cards_str = [str(card) for card in hand]
        board = []
        handList = []
        if communal_cards:
            for card in communal_cards_strs:
                board.append(Card.new(card))
        for card in hand_cards_str:
            handList.append(Card.new(card))
        evaluator = Evaluator()
        return evaluator.evaluate(board, handList)

    def get_players_winnings(self):
        #print("Computer player's winnings: {}, per hand: {}".format(self.computer_player.winnings,
        #                                                        self.computer_player.winnings / self.hands_played))
        #print("Human player's winnings: {}, per hand: {}".format(self.human_player.winnings,
        #                                                         self.human_player.winnings / self.hands_played))
        return self.opponent_player.winnings / self.hands_played, self.q_learning_player.winnings / self.hands_played


def main(args):
    num_hands = int(args[0])
    opponent = eval(args[1])
    game = Game(500, opponent)
    game.start_game(num_hands)

if __name__ == '__main__':
    main(sys.argv[1:])
