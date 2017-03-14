from enum import Enum
from deck import Deck
from deuces import Card
from deuces import Evaluator


class Counter(dict):
    def __getitem__(self, idx):
        self.setdefault(idx, 0.0)
        return dict.__getitem__(self, idx)

    def incrementAll(self, keys, count):
        for key in keys:
            self[key] += count

    def arg_max(self):
        if len(self.keys()) == 0:
            return None
        all = self.items()
        values = [x[1] for x in all]
        maxIndex = values.index(max(values))
        return all[maxIndex][0]

    def sortedKeys(self):
        sortedItems = self.items()
        compare = lambda x, y: sign(y[1] - x[1])
        sortedItems.sort(cmp=compare)
        return [x[0] for x in sortedItems]

    def totalCount(self):
        return sum(self.values())

    def normalize(self):
        total = float(self.totalCount())
        if total == 0: return
        for key in self.keys():
            self[key] = self[key] / total

    def divideAll(self, divisor):
        divisor = float(divisor)
        for key in self:
            self[key] /= divisor

    def copy(self):
        return Counter(dict.copy(self))

    def __mul__(self, y):
        sum = 0
        x = self
        if len(x) > len(y):
            x, y = y, x
        for key in x:
            if key not in y:
                continue
            sum += x[key] * y[key]
        return sum

    def __radd__(self, y):
        for key, value in y.items():
            self[key] += value

    def __add__(self, y):
        addend = Counter()
        for key in self:
            if key in y:
                addend[key] = self[key] + y[key]
            else:
                addend[key] = self[key]
        for key in y:
            if key in self:
                continue
            addend[key] = y[key]
        return addend

    def __sub__(self, y):
        addend = Counter()
        for key in self:
            if key in y:
                addend[key] = self[key] - y[key]
            else:
                addend[key] = self[key]
        for key in y:
            if key in self:
                continue
            addend[key] = -1 * y[key]
        return addend


class Actions(Enum):
    FOLD = 0
    CALL = 1
    RAISE = 2
    
"""
Returns a value between 1 and 7462 for a 5 card poker hand out of 5, 6, or 7 cards
"""
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

def get_rank(score):
    evaluator = Evaluator()
    rank = evaluator.get_rank_class(score)
    print(evaluator.class_to_string(rank))
    return rank
                
def percentHandStrength(score):
    return score / float(7462)                          
                                  
def possibleStraight(cards):
    card_values = []
    for card in cards:
        cardval = card.value
        if cardval == 1:
            cardval = 14
        card_values.append(cardval)
    if len(cards) == 3:
        for i in range(2,15):
            for j in range(2,15):
                card_values.append(i)
                card_values.sort()
                possibleStraight = True
                for k in range(len(card_values) - 1):
                    if card_values[k] + 1 != card_values[k+1]:
                        possibleStraight = False
                if possibleStraight:
                    return True
                card_values.remove(j)
            card_values.remove(i)

    elif len(cards) == 4:
        for i in range(2, 15):
            card_values.append(i)
            card_values.sort()
            possibleStraight = True
            for k in range(len(card_values) - 1):
              if card_values[k] + 1 != card_values[k+1]:
                  possibleStraight = False
            if possibleStraight:
              return True
            card_values.remove(i)
    else:
        return False


class PreflopEvaluator:
    @staticmethod
    def get_range_score(hand):
        """
        evaluates the range of two cards in preflop hand.
        Cards that are closer together are better, and a max range of 5, so this
        returns 6 - diff(card values) or 0 if they are greater than 5 apart.
        :param hand: list of two cards
        :return:
        """
        value0 = hand[0].value
        value1 = hand[1].value
        #check aces
        if value0 == 1:
            value0 = 14
        if value1 == 1:
            value1 = 14
        return 6 - abs(value0 - value1)

    @staticmethod
    def get_pair_score(hand):
        """
        :param hand: list of two cards
        :return: returns 1 if pocket pairs else 0
        """
        return hand[0].value == hand[1].value

    @staticmethod
    def get_flush_score(hand):
        """
        :param hand: list of two cards
        :return: returns 1 if same suit else 0
        """
        return hand[0].suit == hand[1].suit

    @staticmethod
    def evaluate_cards(hand):
        card_stats = Counter()
        hand = list(hand)
        card_stats['range-score'] = PreflopEvaluator.get_range_score(hand)
        card_stats['pair-score'] = PreflopEvaluator.get_pair_score(hand)
        card_stats['flush-score'] = PreflopEvaluator.get_flush_score(hand)
        return card_stats


class BiddingRound(Enum):
    PREFLOP = 0
    POST_FLOP = 1
    SHOWDOWN = 2