import random
from collections import namedtuple


class Deck:
    def __init__(self) -> None:
        self.deck = None
        self.special_mappings = {1: 'Ace', 11: 'Jack', 12: 'Queen', 13: 'King'}

    def reset(self) -> None:
        self._get_full_shuffled_deck()

    def get_card(self) -> namedtuple:
        card = self.deck.pop()
        return card

    def _get_full_shuffled_deck(self) -> None:
        Card = namedtuple('Card', ['suit', 'value'])
        suits = random.SystemRandom().sample(
            ['hearts', 'diamonds', 'spades', 'clubs'], 4
        )
        self.deck = [
            Card(suit, value)
            for value in random.SystemRandom().sample(range(1, 14), 13)
            for suit in suits
        ]
        self.deck = random.SystemRandom().sample(self.deck, len(self.deck))
