import random
from util import Counter
from util import Actions
from util import PreflopEvaluator
from util import evalHand
from util import get_rank
from util import percentHandStrength
from util import possibleStraight
from util import BiddingRound
import pickle

class Player:
    def __init__(self, chips):
        self.hand = []
        self.chips = chips
        self.winnings = 0
        self.stats = Counter()
        self.actions = []
        self.hand_features = []  # holds list of (game_state,action) pairs for training once we know whether we won or not
        self.learning_rate = 0.01

    def add_card_to_hand(self, card):
        self.hand.append(card)

    def reset_chips(self, chip_amount):
        self.chips = chip_amount

    def get_hand(self):
        return self.hand

    def is_out(self):
        return self.chips <= 0

    def ante(self, value):
        value = min(self.chips, value)
        self.chips -= value
        return value

    def won(self, total_chips, pool_amt):
        this_winnings = self.chips - total_chips + pool_amt
        self.winnings += this_winnings

    def loss(self, total_chips, pool_amt):
        this_winnings = self.chips - total_chips
        self.winnings += this_winnings

    def clear_hand(self):
        self.hand = []
        self.hand_features = []

    def get_stats(self):
        if len(self.actions) > 0:
            self.stats['raise-rate'] = sum([action == Actions.RAISE for action in self.actions]) / len(self.actions)
            self.stats['fold-rate'] = sum(action == Actions.FOLD for action in self.actions) / len(self.actions)
            self.stats['call-rate'] = sum(action == Actions.CALL for action in self.actions) / len(self.actions)
        return self.stats

    def get_legal_actions(self, game_state, bid_amount, raise_amount):
        if self.chips <= 0 or raise_amount > self.chips:
            return [Actions.FOLD, Actions.CALL]
        else:
            return list(Actions)

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
    def __init__(self, chips, adversary_type=None):
        super().__init__(chips)
        self.adversary_type = adversary_type
        self.q_learning_weights = self.load_q_learning_weights()

    def get_computer_bid(self, game_state, bid_amount, raise_amount):
        print(game_state)
        action = self.get_q_star_action(game_state, bid_amount, raise_amount)
        self.actions.append(action)
        return action

    def make_q_learning_dict_from_state(self, game_state):
        q_learning_dict = Counter()
        key_template = "PREFLOP" if game_state["bidding-round"] == BiddingRound.PREFLOP else "POSTFLOP"
        for key, value in game_state.items():
            if type(value) in [int, bool, float]:
                q_learning_dict["{}-{}".format(key_template, key)] = value
            elif key == "communal-cards":
                if len(value) == 0: # use preflop evaluator
                    preflop_scores = PreflopEvaluator.evaluate_cards(self.hand)
                    for key2, value2 in preflop_scores.items():
                        q_learning_dict["{}-hand-{}".format(key_template, key2)] = value2
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
        weights_list = [abs(weight) for weight in weights.values()]
        weights_list.append(1)
        max_val = max(weights_list) or 1
        weights.divideAll(max_val)
        print(weights)
        self.q_learning_weights = weights
        self.hand_features = []

    def get_bid(self, game_state, bid_amount, raise_amount):
        print("Computer cards:")
        self.print_hand()
        action = self.get_q_star_action(game_state, bid_amount, raise_amount)
        self.hand_features.append((game_state, action))
        return self.get_q_star_action(game_state, bid_amount, raise_amount)

    def get_q_learning_weights_filename(self):
        file_template = "learning_data/q_learning_weights_{}.p"
        type_fillins = {
            RandomPlayer: "random",
            QLearningPlayer: "meta",
            TightPlayer: "tight",
            AggressivePlayer: "aggressive"
        }
        if self.adversary_type not in type_fillins:
            filename = file_template.format(type_fillins[random.choice(list(type_fillins.keys()))])
        else:
            filename = file_template.format(type_fillins[self.adversary_type])
        return filename

    def load_q_learning_weights(self):
        try:
            weights = pickle.load(self.get_q_learning_weights_filename(), "b")
        except:
            weights = Counter()
        return weights

    def store_q_learning_weights(self):
        weights = self.q_learning_weights
        pickle.dump(weights, open(self.get_q_learning_weights_filename(), "wb"))


class HumanPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)

    def get_human_bid(self, game_state, bid_amount, raise_amount):
        print(game_state)
        communal_cards = game_state['communal-cards']
        action = None
        Player.print_communal_cards(communal_cards)
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        print("The pot is now: {}".format(game_state["pool-amount"]))
        print("The raise amount is {} and the call amount is {}".format(raise_amount, bid_amount))
        print("You have {} chips".format(self.chips))
        print("Your hand is {}".format(hcs))
        print("Your legal actions are: {}".format(self.get_legal_actions(game_state, bid_amount, raise_amount)))
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
        return self.get_human_bid(game_state, bid_amount, raise_amount)


class RandomPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)

    def get_bid(self, game_state, bid_amount, raise_amount):
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        return random.choice(actions)
      
class TightPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)
    
    def get_features(self, game_state):
        features = Counter()
        for key, value in game_state.items():
            if type(value) in [int, bool, float]:
                features[key] = value
            elif key == "communal-cards":
                if len(value) == 0: # use preflop evaluator
                    preflop_scores = PreflopEvaluator.evaluate_cards(self.hand)
                    for key2, value2 in preflop_scores.items():
                        features["hand-{}".format(key2)] = value2
                else:
                    handScore = evalHand(self.hand, value)
                    features["score"] = handScore
                    print("HandScore: ",handScore)
                    percentHandScore = percentHandStrength(handScore)
                    features["percentScore"] = percentHandScore
                    print("percentHandScore: ",percentHandScore)
                    handRank = get_rank(handScore)
                    preflop_scores = PreflopEvaluator.evaluate_cards(self.hand)
                    flush_score = 0
                    if handRank != 4:
                        if preflop_scores['flush-score'] == 1:
                            flush_score = 2
                            for card in value:
                                if self.hand[0].suit == card.suit:
                                    flush_score += 1
                        if (5-flush_score) <= (5 - len(value)):
                            features["possible-flush"] = True
                    if handRank != 5:
                        all_cards = self.hand + value
                        features["possible-straight"] = possibleStraight(all_cards)
           
                    for key2, value2 in preflop_scores.items():
                        features["hand-{}".format(key2)] = value2
                   
                    
        return features
    
    
    def get_bid(self, game_state, bid_amount, raise_amount):
        self.print_hand()
        features = self.get_features(game_state)
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        ace = False
        for card in self.hand:
            if card.value == 1:
                ace = True
        #pre flop
        if features["score"] == 0:
            if bid_amount < 10: #limp or call
                #suited connectors
                if features["hand-flush-score"] == 1 and features["hand-range-score"] > 3:
                    return Actions.CALL
                #pairs
                elif features["hand-pair-score"] == 1:
                    if self.hand[0].value > 9:
                        return Actions.RAISE
                    else:
                        return Actions.CALL
                #Aces and Kings
                elif max(self.hand[0].value, self.hand[1].value) > 12 or ace:
                    if features["hand-flush-score"] == 1:
                        return Actions.RAISE
                    elif ace and max(self.hand[0].value, self.hand[1].value) > 7:
                        return Actions.RAISE
                    elif (not ace) and min(self.hand[0].value, self.hand[1].value) > 9 :
                        return Actions.RAISE
                    else:
                        return Actions.CALL
                elif max(self.hand[0].value, self.hand[1].value) > 8:
                    if features["hand-range-score"] > 3:
                        return Actions.CALL
                    else:
                        return Actions.FOLD
                else:
                    return Actions.FOLD
            #they reraised
            else:
                if ace and features["hand-pair-score"] == 1: #If we have pocket aces raise
                    return Actions.RAISE
                if ace:
                    if self.hand[0].value + self.hand[1].value > 7: #If we have a decent kicker call
                        return Actions.CALL
                elif self.hand[0].value + self.hand[1].value > 20: #If our cards are high
                    if features["hand-pair-score"] == 1 and self.hand[0].value > 11: #if we have a pair
                        return Actions.RAISE
                    else:
                        return Actions.CALL
                else:
                    if random.random() > .75: #most of the time fold but sometimes call so we dont get exploited
                        return Actions.CALL
                    else:
                        return Actions.FOLD
            return Actions.FOLD #all unconsidered cases fold

        #post flop
        else:
            if features["percentScore"] < .3 and features["percentScore"]:
                return Actions.RAISE
            if features["percentScore"] < .3:
                return Actions.RAISE
            elif features["percentScore"] > .3 and features["percentScore"] < .8:
                return Actions.CALL
            else:
                if Actions.FOLD in actions: #if we can't check fold otherwise check
                    return Actions.FOLD
                else:
                    return Actions.CALL
        #print(actions)
        return Actions.FOLD
      
class AggressivePlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)

    def get_bid(self, game_state, bid_amount, raise_amount):
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        return random.choice(actions)
      


