import random
from util import Counter
from util import Actions
from util import PreflopEvaluator
from util import evalHand
from util import get_rank
from util import percentHandStrength
from util import possibleStraight
from util import possibleFlush
from util import BiddingRound
import pickle

class Player:
    def __init__(self, chips):
        self.hand = []
        self.chips = chips
        self.winnings = 0
        self.first_half_winnings = 0
        self.last_half_winnings = 0
        self.stats = Counter()
        self.actions = []
        self.hand_features = []  # holds list of (game_state,action) pairs for training once we know whether we won or not
        self.learning_rate = 0.01
        self.hands_played = 1
        self.pfr = 0
        self.vpip = 0
        self.updated_pfr = False
        self.updated_vpip = False
        self.won_at_showdown = 0
        self.played_to_showdown = 1

    def get_stats(self):
        if len(self.actions) > 0:
            self.stats['raise-rate'] = sum([action == Actions.RAISE for action in self.actions]) / len(self.actions)
            self.stats['fold-rate'] = sum(action == Actions.FOLD for action in self.actions) / len(self.actions)
            self.stats['call-rate'] = sum(action == Actions.CALL for action in self.actions) / len(self.actions)
            self.stats['vpip'] = self.vpip / self.hands_played
            self.stats['pfr'] = self.pfr / self.hands_played
            if not self.stats['call-rate'] == 0:
                self.stats['aggression-factor'] = self.stats['raise-rate'] / self.stats['call-rate'] / 10.0
            self.stats['won-at-showdown'] = self.won_at_showdown / self.played_to_showdown
        return self.stats

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

    def won(self, total_chips, pool_amt, showdown=False):
        this_winnings = self.chips - total_chips + pool_amt
        self.winnings += this_winnings
        if self.hands_played < 501:
            self.first_half_winnings += this_winnings
        else:
            self.last_half_winnings += this_winnings
        self.updated_vpip = False
        self.updated_pfr = False
        self.hands_played += 1
        if showdown:
            self.played_to_showdown += 1
            self.won_at_showdown += 1

    def loss(self, total_chips, pool_amt, showdown=False):
        this_winnings = self.chips - total_chips
        self.winnings += this_winnings
        if self.hands_played < 501:
            self.first_half_winnings += this_winnings
        else:
            self.last_half_winnings += this_winnings
        self.updated_vpip = False
        self.updated_pfr = False
        self.hands_played += 1
        if showdown:
            self.played_to_showdown += 1

    def clear_hand(self):
        self.hand = []
        self.hand_features = []

    def get_legal_actions(self, game_state, bid_amount, raise_amount):
        if self.chips <= 0 or raise_amount > self.chips:
            return [Actions.FOLD, Actions.CALL]
        elif game_state["betting-round"] == BiddingRound.PREFLOP and \
                        game_state["first-player"] is not self and game_state["no-bets"]:
            return [Actions.CALL, Actions.RAISE]
        elif game_state["betting-round"] == BiddingRound.POST_FLOP and game_state["no-bets"]:
            return [Actions.CALL, Actions.RAISE]
        else:
            return list(Actions)

    @staticmethod
    def print_communal_cards(communal_cards):
        commuanl_cards_strs = " " * 20 + "*" * 19 + "\n"
        commuanl_cards_strs += " " * 20
        commuanl_cards_strs += "  ".join(["{}".format(card.to_str()) for card in communal_cards])
        commuanl_cards_strs += "\n" + " " * 20 + "*" * 19 + "\n"
        #print("\n{}\n".format(commuanl_cards_strs))

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
        ##print(game_state)
        action = self.get_q_star_action(game_state, bid_amount, raise_amount)
        self.actions.append(action)
        return action

    def make_q_learning_dict_from_state(self, game_state, action):
        q_learning_dict = Counter()
        player1 = game_state["player-1"]
        player2 = game_state["player-2"]
        opponent = player1 if player1 is not self else player2
        key_template = "PREFLOP" if game_state["betting-round"] == BiddingRound.PREFLOP else "POSTFLOP"
        key_template = "{}-{}".format(key_template, action)
        for key, value in game_state.items():
            if type(value) in [int, bool, float]:
                q_learning_dict["{}-{}".format(key_template, key)] = value
            elif key == "communal-cards":
                if len(value) == 0: # use preflop evaluator
                    preflop_scores = PreflopEvaluator.evaluate_cards(self.hand)
                    for key2, value2 in preflop_scores.items():
                        q_learning_dict["{}-hand-{}".format(key_template, key2)] = value2
                elif len(value) < 5:
                    hand_score = evalHand(self.hand, value)
                    q_learning_dict["{}-straight-communal-cards".format(key_template)] =\
                        possibleStraight(list(set(value).union(set(self.hand))))
                    q_learning_dict["{}-flush-communal-cards".format(key_template)] =\
                        possibleFlush(list(set(value).union(set(self.hand))))
                    q_learning_dict["{}-percent-communal-cards".format(key_template)] =\
                        percentHandStrength(hand_score)
                    q_learning_dict["{}-handrank".format(key_template)] =\
                        get_rank(hand_score)
                else:
                    hand_score = evalHand(self.hand, value)
                    percentHandScore = percentHandStrength(hand_score)
                    board_score = evalHand(value[0:2], value[2:])
                    percentBoardScore = percentHandStrength(board_score)
                    diffScore = percentHandScore - percentBoardScore
                    q_learning_dict["{}-percent-communal-cards".format(key_template)] =\
                        percentHandStrength(hand_score)
                    q_learning_dict["{}-handrank".format(key_template)] =\
                        get_rank(hand_score)
                    q_learning_dict["{}-diffscore".format(key_template)] =\
                        get_rank(diffScore)

        if (not (game_state["betting-round"] == BiddingRound.PREFLOP and game_state["no-bids"])) and len(self.actions) > 0\
                and len(opponent.actions) > 0:
            q_learning_dict["{}-opponent-just-raised".format(key_template)] =\
                opponent.actions[len(opponent.actions) - 1] == Actions.RAISE
            q_learning_dict["{}-player-just-raised".format(key_template)] =\
                self.actions[len(self.actions) - 1] == Actions.RAISE
        ##print(q_learning_dict)
        q_learning_dict.divideAll(10.0)
        return q_learning_dict

    def won(self, total_chips, pool_amt, showdown=False):
        this_winnings = self.chips - total_chips + pool_amt
        self.winnings += this_winnings
        self.update_weights(this_winnings)
        if this_winnings > 100:
            pass
            #self.print_hand()
        if self.hands_played < 501:
            self.first_half_winnings += this_winnings
        else:
            self.last_half_winnings += this_winnings
        self.updated_vpip = False
        self.updated_pfr = False
        self.hands_played += 1
        if showdown:
            self.played_to_showdown += 1
            self.won_at_showdown += 1

    def loss(self, total_chips, pool_amt, showdown=False):
        this_winnings = self.chips - total_chips
        self.winnings += this_winnings
        if self.hands_played < 501:
            self.first_half_winnings += this_winnings
        else:
            self.last_half_winnings += this_winnings
        if this_winnings < -100:
            self.print_hand()
            print(self.actions[-1])
        self.update_weights(this_winnings)
        self.updated_vpip = False
        self.updated_pfr = False
        self.hands_played += 1
        if showdown:
            if self.chips == 0:
                pass
                #print("player is all in")
            self.played_to_showdown += 1

    def get_q_value(self, game_state, action):
        q_learning_dict = self.make_q_learning_dict_from_state(game_state, action)
        score = 0.0
        for key in q_learning_dict:
            if (q_learning_dict[key] is None) or (self.q_learning_weights[key] is None):
                #print('hi')
                pass
            try:
                score += q_learning_dict[key] * self.q_learning_weights[key]
            except:
                pass
        return score

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
            difference = (winnings / 1000) - self.get_q_value(state, action)
            #print(difference)
            q_learning_dict = self.make_q_learning_dict_from_state(state, action)
            for feature in q_learning_dict:
                weights[feature] += self.learning_rate * difference * q_learning_dict[feature]
        ##print(weights)
        self.q_learning_weights = weights
        self.hand_features = []

    def get_bid(self, game_state, bid_amount, raise_amount):
        #print("Computer cards:")
        #self.print_hand()
        action = self.get_q_star_action(game_state, bid_amount, raise_amount)
        if random.random() > -0.1:
            true_action = action
        else:
           true_action = random.choice(list(self.get_legal_actions(game_state, bid_amount, raise_amount)))
        #true_action = action
        if game_state["betting-round"] == BiddingRound.PREFLOP:
            if true_action == Actions.RAISE:
                if not self.updated_vpip:
                    self.vpip += 1
                    self.updated_vpip = True
                if not self.updated_pfr:
                    self.updated_pfr = True
                    self.pfr += 1
            elif true_action == Actions.CALL:
                if not (self is not game_state["first-player"] and game_state["no-bets"]):
                    if not self.updated_vpip:
                        self.vpip += 1
                        self.updated_vpip = True
        self.actions.append(true_action)
        self.hand_features.append((game_state, true_action))
        return true_action

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
        communal_cards = game_state['communal-cards']
        action = None
        Player.print_communal_cards(communal_cards)
        hand_cards_str = [card.to_str() for card in self.hand]
        hcs = ", ".join(hand_cards_str)
        #print("The pot is now: {}".format(game_state["pool-amount"]))
        #print("The raise amount is {} and the call amount is {}".format(raise_amount, bid_amount))
        #print("You have {} chips".format(self.chips))
        #print("Your hand is {}".format(hcs))
        #print("Your legal actions are: {}".format(self.get_legal_actions(game_state, bid_amount, raise_amount)))
        bid = input("Would you like to [f]old, [c]all, or [r]aise?\n")
        if bid[0] == 'f':
            action = Actions.FOLD
        elif bid[0] == 'c':
            action = Actions.CALL
        else:
            action = Actions.RAISE
        true_action = action
        if game_state["betting-round"] == BiddingRound.PREFLOP:
            if true_action == Actions.RAISE:
                if not self.updated_vpip:
                    self.vpip += 1
                    self.updated_vpip = True
                if not self.updated_pfr:
                    self.updated_pfr = True
                    self.pfr += 1
            elif true_action == Actions.CALL:
                if not (self is not game_state["first-player"] and game_state["no-bets"]):
                    if not self.updated_vpip:
                        self.vpip += 1
                        self.updated_vpip = True
        self.actions.append(action)
        return action

    def get_bid(self, game_state, bid_amount, raise_amount):
        return self.get_human_bid(game_state, bid_amount, raise_amount)


class RandomPlayer(Player):
    def __init__(self, chips):
        super().__init__(chips)

    def get_bid(self, game_state, bid_amount, raise_amount):
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        true_action = random.choice(actions)
        self.actions.append(true_action)
        if game_state["betting-round"] == BiddingRound.PREFLOP:
            if true_action == Actions.RAISE:
                if not self.updated_vpip:
                    self.vpip += 1
                    self.updated_vpip = True
                if not self.updated_pfr:
                    self.updated_pfr = True
                    self.pfr += 1
            elif true_action == Actions.CALL:
                if not (self is not game_state["first-player"] and game_state["no-bets"]):
                    if not self.updated_vpip:
                        self.vpip += 1
                        self.updated_vpip = True
        return true_action


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

                    percentHandScore = percentHandStrength(handScore)
                    features["percentScore"] = percentHandScore

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
        features = self.get_features(game_state)
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        action = None
        ace = False
        for card in self.hand:
            if card.value == 1:
                ace = True
        #pre flop
        if features["score"] == 0:
            if bid_amount < 10: #limp or call
                #suited connectors
                if features["hand-flush-score"] == 1 and features["hand-range-score"] > 3:
                    action = Actions.CALL
                #pairs
                elif features["hand-pair-score"] == 1:
                    if self.hand[0].value > 9:
                        action = Actions.RAISE
                    else:
                        action = Actions.CALL
                #Aces and Kings
                elif max(self.hand[0].value, self.hand[1].value) > 12 or ace:
                    if features["hand-flush-score"] == 1:
                        action = Actions.RAISE
                    elif ace and max(self.hand[0].value, self.hand[1].value) > 7:
                        action = Actions.RAISE
                    elif (not ace) and min(self.hand[0].value, self.hand[1].value) > 9 :
                        action = Actions.RAISE
                    else:
                        action = Actions.CALL
                elif max(self.hand[0].value, self.hand[1].value) > 8:
                    if features["hand-range-score"] > 3:
                        action = Actions.CALL
                    else:
                        action = Actions.FOLD
                else:
                    action = Actions.FOLD
            #they reraised
            else:
                if ace and features["hand-pair-score"] == 1: #If we have pocket aces raise
                    action = Actions.RAISE
                if ace:
                    if self.hand[0].value + self.hand[1].value > 7: #If we have a decent kicker call
                        action = Actions.CALL
                elif self.hand[0].value + self.hand[1].value > 20: #If our cards are high
                    if features["hand-pair-score"] == 1 and self.hand[0].value > 11: #if we have a pair
                        action = Actions.RAISE
                    else:
                        action = Actions.CALL
                else:
                    if random.random() > .75: #most of the time fold but sometimes call so we dont get exploited
                        action = Actions.CALL
                    else:
                        action = Actions.FOLD
            return Actions.FOLD #all unconsidered cases fold

        #post flop
        else:
            if features["percentScore"] < .3 and features["percentScore"]:
                action = Actions.RAISE
            if features["percentScore"] < .3:
                action = Actions.RAISE
            elif features["percentScore"] > .3 and features["percentScore"] < .8:
                action = Actions.CALL
            else:
                if Actions.FOLD in actions: #if we can't check fold otherwise check
                    if features["possible-straight"]:
                        if ace:
                            action = Actions.CALL
                        elif self.hand[0].value + self.hand[1].value > 22:
                            action = Actions.CALL
                        elif features["possible-flush"]:
                            action = Actions.CALL
                        else:
                            action = Actions.FOLD
                    elif features["possible-flush"]:
                        if ace:
                            action = Actions.CALL
                        elif self.hand[0].value + self.hand[1].value > 22:
                            action = Actions.CALL
                        elif features["possible-straight"]:
                            action = Actions.CALL
                        else:
                            action = Actions.FOLD
                    else:
                        action = Actions.FOLD
                else:
                    action = Actions.CALL
        self.actions.append(action)
        true_action = action
        if game_state["betting-round"] == BiddingRound.PREFLOP:
            if true_action == Actions.RAISE:
                if not self.updated_vpip:
                    self.vpip += 1
                    self.updated_vpip = True
                if not self.updated_pfr:
                    self.updated_pfr = True
                    self.pfr += 1
            elif true_action == Actions.CALL:
                if not (self is not game_state["first-player"] and game_state["no-bets"]):
                    if not self.updated_vpip:
                        self.vpip += 1
                        self.updated_vpip = True
        return action or Actions.FOLD

class AggressivePlayer(Player):
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
                    percentHandScore = percentHandStrength(handScore)
                    features["percentScore"] = percentHandScore
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
        features = self.get_features(game_state)
        actions = self.get_legal_actions(game_state, bid_amount, raise_amount)
        action = None
        ace = False
        for card in self.hand:
            if card.value == 1:
                ace = True
        #pre flop
        if features["score"] == 0:
            if bid_amount < 10: #limp or call
                #pairs
                if features["hand-pair-score"] == 1:
                    action = Actions.RAISE
                #Aces and Kings
                elif max(self.hand[0].value, self.hand[1].value) > 11 or ace:
                    if features["hand-flush-score"] == 1:
                        action = Actions.RAISE
                    elif ace and max(self.hand[0].value, self.hand[1].value) > 4:
                        action = Actions.RAISE
                    elif (not ace) and min(self.hand[0].value, self.hand[1].value) > 6 :
                        action = Actions.RAISE
                    else:
                        action = Actions.CALL
                #suited connectors
                elif features["hand-flush-score"] == 1 and features["hand-range-score"] > 1:
                    action = Actions.CALL
                elif max(self.hand[0].value, self.hand[1].value) > 8:
                    if features["hand-range-score"] > 1:
                        action = Actions.CALL
                    else:
                        if Actions.FOLD in actions:
                            action = Actions.FOLD
                        else:
                            action = Actions.CALL
                else:
                    if Actions.FOLD in actions:
                        action = Actions.FOLD
                    else:
                        action = Actions.CALL

            #they reraised
            else:
                if ace and features["hand-pair-score"] == 1: #If we have pocket aces raise
                    action = Actions.RAISE
                elif ace:
                    if self.hand[0].value + self.hand[1].value > 12: #If we have a decent kicker call
                        action = Actions.RAISE
                    else:
                        action = Actions.CALL
                elif self.hand[0].value + self.hand[1].value > 15: #If our cards are high
                    if features["hand-pair-score"] == 1 and self.hand[0].value > 8: #if we have a pair
                        action = Actions.RAISE
                    else:
                        action = Actions.CALL
                else:
                    if random.random() > .4: #most of the time fold but sometimes call so we dont get exploited
                        action = Actions.CALL
                    else:
                        if Actions.FOLD in actions:
                            action = Actions.FOLD
                        else:
                            action = Actions.CALL

        #post flop
        else:
            if features["percentScore"] < .5:
                action = Actions.RAISE
            elif features["percentScore"] > .5 and features["percentScore"] < .9:
                action = Actions.CALL
            else:
                if Actions.FOLD in actions: #if we can't check fold otherwise check
                    if features["possible-straight"]:
                        if ace:
                            action = Actions.CALL
                        elif self.hand[0].value + self.hand[1].value > 18:
                            action = Actions.CALL
                        elif features["possible-flush"]:
                            action = Actions.CALL
                        else:
                            action = Actions.FOLD
                    elif features["possible-flush"]:
                        if ace:
                            action = Actions.CALL
                        elif self.hand[0].value + self.hand[1].value > 18:
                            action = Actions.CALL
                        elif features["possible-straight"]:
                            action = Actions.CALL
                        else:
                            action = Actions.FOLD
                    else:
                        action = Actions.FOLD
                else:
                    action = Actions.CALL
        self.actions.append(action)
        true_action = action
        if game_state["betting-round"] == BiddingRound.PREFLOP:
            if true_action == Actions.RAISE:
                if not self.updated_vpip:
                    self.vpip += 1
                    self.updated_vpip = True
                if not self.updated_pfr:
                    self.updated_pfr = True
                    self.pfr += 1
            elif true_action == Actions.CALL:
                if not (self is not game_state["first-player"] and game_state["no-bets"]):
                    if not self.updated_vpip:
                        self.vpip += 1
                        self.updated_vpip = True
        return action or Actions.FOLD
