class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value + 1

    def __lt__(self, other):
        if self.value == other.value:
            return self.suit < other.suit
        return self.value < other.value

    def __gt__(self, other):
        return not self.__lt__(other)

    def __eq__(self, other):
        return self.suit == other.suit and self.value == other.value

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        suit_dict = {
            3: "s",
            2: "h",
            1: "d",
            0: "c"
        }
        value_str = None
        if self.value == 1:
            value_str = "A"
        elif self.value <= 9:
            value_str = str(self.value)
        elif self.value == 10:
            value_str = "T"
        elif self.value == 11:
            value_str = "J"
        elif self.value == 12:
            value_str = "Q"
        elif self.value == 13:
            value_str = "K"
        return "{}{}".format(value_str, suit_dict[self.suit])

    def to_str(self):
        suit_dict = {
            3: "♠",
            2: "♥",
            1: "♦",
            0: "♣"
        }
        value_str = None
        if self.value == 1:
            value_str = "A"
        elif self.value <= 10:
            value_str = str(self.value)
        elif self.value == 11:
            value_str = "J"
        elif self.value == 12:
            value_str = "Q"
        elif self.value == 13:
            value_str = "K"
        return "{}{}".format(value_str, suit_dict[self.suit])


class Deck:
    def __init__(self):
        cards = []
        for suit in range(4):
            for value in range(13):
                cards.append(Card(suit, value))
        self.cards = cards

    def shuffle(self):
        from random import shuffle
        shuffle(self.cards)

    def pop(self):
        return self.cards.pop()

    def __str__(self):
        str_list = [str(card) for card in self.cards]
        s = ", ".join(str_list)
        return s


def main():
    deck = Deck()
    deck.shuffle()
    print(deck)

if __name__ == '__main__':
    main()
