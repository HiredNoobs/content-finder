from cytubebot.blackjack.common import get_ascii_art, get_hidden_ascii_art


class Player:
    def __init__(self, chips: int) -> None:
        self.chips = chips
        self._bet = 0
        self.hand = []
        self._error = None
        self._command = None
        self.result = None

    def reset(self) -> None:
        self._bet = 0
        self.hand = []
        self._error = None
        self._command = None
        self.result = None

    def check_split_available(self) -> bool:
        return len(self.hand) == 2 and self.hand[0].value == self.hand[1].value

    def check_blackjack(self) -> bool:
        values = [x.value if x.value < 10 else 10 if x.value != 1 else 11 for x in self.hand]
        if sum(values) == 21:
            return True
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

    def get_hand_ascii(self):
        result = []
        for card in self.hand:
            result += get_ascii_art(card)

        return result

    @property
    def error(self) -> str:
        err = self._error
        self._error = None
        return err

    @property
    def bet(self) -> int:
        return self._bet

    @bet.setter
    def bet(self, val: int) -> None:
        """Set the players bet, assumes that val is already an int"""
        if not isinstance(val, int):
            self._error = 'bet received not integer value.'
        if val > self.chips:
            self._error = f'Cannot bet more chips than you have. {val} > {self.chips}'
            return
        self._bet = val

    @property
    def command(self) -> str:
        command = self._command
        self._command = None
        return command

    @command.setter
    def command(self, command: str) -> None:
        self._command = command
