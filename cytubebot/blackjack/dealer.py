from collections import namedtuple
from cytubebot.blackjack.deck import Deck
from cytubebot.blackjack.common import get_ascii_art, get_hidden_ascii_art


class Dealer:
    def __init__(self) -> None:
        self.deck = Deck()
        self.hand = []
        self.dealer_stands_val = 17  # The value the dealer stands at
        self.result = None

    def reset(self) -> None:
        self.deck.reset()
        self.hand = []
        self.result = None

    def get_card_from_deck(self) -> namedtuple:
        """Wrapped func for blackjack_bot to reach the deck"""
        card = self.deck.get_card()
        return card

    def check_blackjack(self) -> bool:
        # Get values for cards in hand, convers all aces to high (11)
        values = [x.value if x.value < 10 else 10 if x.value != 1 else 11 for x in self.hand]
        if sum(values) == 21:
            return True
        # Convert aces to 1, one by one checking each for blackjack
        while 11 in values:
            keys = [key for key, val in enumerate(values) if val == 11]
            values[keys[0]] = 1
            if sum(values) == 21:
                return True
        
        return False

    def check_bust(self) -> bool:
        values = [x.value if x.value < 10 else 10 if x.value != 1 else 11 for x in self.hand]
        if sum(values) > 21:
            return True
        while 11 in values:
            keys = [key for key, val in enumerate(values) if val == 11]
            values[keys[0]] = 1
            if sum(values) == 21:
                return True
        
        return False

    def check_stand(self) -> bool:
        """Returns True if dealer must stand"""
        # Get values for cards in hand, leaves all aces low
        values = [x.value if x.value < 10 else 10 for x in self.hand]
        
        if sum(values) >= self.dealer_stands_val:
            return True

        return False

    def set_result(self) -> None:
        if self.check_bust():
            return
        elif self.check_blackjack():
            self.result = 21
        else:
            possible_results = []
            # If not blackjack or bust then find the best result
            values = [x.value if x.value < 10 else 10 if x.value != 1 else 11 for x in self.hand]
            possible_results.append(sum(values))

            while 11 in values:
                keys = [key for key, val in enumerate(values) if val == 11]
                values[keys[0]] = 1
                possible_results.append(sum(values))
            
            # Remove all busts
            possible_results = [x for x in possible_results if x <= 21]

            # Set result to highest possible result
            self.result = max(possible_results)

    def get_hand_ascii(self, show_hidden=False):
        result = []
        for i, card in enumerate(self.hand):
            print(f'ascii: {result}')
            if i == 0 and not show_hidden:
                result += get_hidden_ascii_art()
            else:
                tmp = get_ascii_art(card)
                result += tmp

        return result
