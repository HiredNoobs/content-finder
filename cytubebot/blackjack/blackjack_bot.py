import random
import socketio

from cytubebot.common.socket_extensions import send_chat_msg


class BlackjackBot:
    def __init__(self, socket: socketio, num_players=1, initial_balance=100):
        # Socket will be used as 'write' only i.e. the main bot will handle
        # all the main reading so that we don't process everything twice.
        self._sio = socket
        self.num_players = num_players
        self.players = [self.create_player(initial_balance) for _ in range(num_players)]
        self.deck = self.create_deck()
        self.dealer_hand = []

    def process_command(self, user, command, args) -> None:
        match command:
            # case '!start_blackjack':
            #     self.play()
            case '!stop_blackjack':
                print('STOP')

    def create_player(self, initial_balance):
        return {
            'hand': [],
            'split_hand': [],
            'balance': initial_balance
        }

    def create_deck(self):
        """Create a standard deck of cards."""
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        deck = [{'rank': rank, 'suit': suit} for rank in ranks for suit in suits]
        random.shuffle(deck)
        return deck

    def deal_card(self, hand):
        """Deal a card from the deck to a hand."""
        card = self.deck.pop()
        hand.append(card)

    def calculate_hand_value(self, hand):
        """Calculate the value of a hand."""
        value = 0
        num_aces = 0
        for card in hand:
            rank = card['rank']
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                num_aces += 1
            else:
                value += int(rank)

        # Handle aces
        for _ in range(num_aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        return value

    def place_bet(self, player):
        """Place a bet for a player."""
        while True:
            try:
                bet = int(input(f"Player {self.players.index(player) + 1}, your balance: {player['balance']}. Place your bet: "))
                if bet <= 0 or bet > player['balance']:
                    msg = "Invalid bet. Please enter a valid amount."
                    send_chat_msg(self._sio, msg)
                else:
                    player['balance'] -= bet
                    return bet
            except ValueError:
                msg = "Invalid input. Please enter a valid integer."
                send_chat_msg(self._sio, msg)

    def split(self, player):
        """Split a player's hand into two separate hands."""
        if len(player['hand']) == 2 and player['hand'][0]['rank'] == player['hand'][1]['rank']:
            player['split_hand'].append([player['hand'].pop(), self.deck.pop()])
            player['hand'].append(self.deck.pop())
            msg = f"Player {self.players.index(player) + 1} has split their hand!"
            send_chat_msg(self._sio, msg)

    def double_down(self, player, bet):
        """Double down a player's bet and deal one more card."""
        if len(player['hand']) == 2:
            player['balance'] -= bet
            self.deal_card(player['hand'])
            msg = f"Player {self.players.index(player) + 1} has doubled down!"
            send_chat_msg(self._sio, msg)

    def player_action(self, player, bet):
        """Handle player actions (hit, stand, split, double down)."""
        while True:
            msg = f"Player {self.players.index(player) + 1}, your hand: {player['hand']} (Value: {self.calculate_hand_value(player['hand'])})"
            send_chat_msg(self._sio, msg)
            action = input("Do you want to hit, stand, split, or double down? ").lower()
            if action == 'hit':
                self.deal_card(player['hand'])
                player_value = self.calculate_hand_value(player['hand'])
                if player_value > 21:
                    msg = f"Player {self.players.index(player) + 1} busts! You lose."
                    send_chat_msg(self._sio, msg)
                    player['balance'] -= bet
                    break
            elif action == 'stand':
                break
            elif action == 'split':
                self.split(player)
            elif action == 'double':
                self.double_down(player, bet)
                break
            else:
                msg = "Invalid input. Please enter 'hit', 'stand', 'split', or 'double'."
                send_chat_msg(self._sio, msg)

    def resolve_bets(self, player, dealer_value, bet):
        """Resolve bets for a player based on hand values."""
        hand_value = self.calculate_hand_value(player['hand'])
        if hand_value > 21:
            msg = f"Player {self.players.index(player) + 1} busts! You lose."
            send_chat_msg(self._sio, msg)
            player['balance'] -= bet
        elif dealer_value > 21 or dealer_value < hand_value:
            msg = f"Player {self.players.index(player) + 1} wins! You won {bet} chips."
            send_chat_msg(self._sio, msg)
            player['balance'] += 2 * bet
        elif dealer_value == hand_value:
            msg = f"Player {self.players.index(player) + 1}, it's a tie! Your bet is returned."
            send_chat_msg(self._sio, msg)
            player['balance'] += bet
        else:
            msg = f"Player {self.players.index(player) + 1}, dealer wins. You lose your bet."
            send_chat_msg(self._sio, msg)

    def play(self):
        """Play the multi-player blackjack game."""
        msg = "Starting Blackjack!"
        send_chat_msg(self._sio, msg)

        # Deal initial cards
        for _ in range(2):
            for player in self.players:
                self.deal_card(player['hand'])
            self.deal_card(self.dealer_hand)

        while any(player['balance'] > 0 for player in self.players):
            self.dealer_hand = []
            for player in self.players:
                bet = self.place_bet(player)
                self.player_action(player, bet)
                if player['split_hand']:
                    msg = 'SPLIT HAND ROUND'
                    send_chat_msg(self._sio, msg)
                    player['hand'] = player['split_hand']
                    self.player_action(player, bet)

            # Dealer's turn
            while self.calculate_hand_value(self.dealer_hand) < 17:
                self.deal_card(self.dealer_hand)
            dealer_value = self.calculate_hand_value(self.dealer_hand)
            msg = f"Dealer's hand: {self.dealer_hand} (Value: {dealer_value})"
            send_chat_msg(self._sio, msg)

            # Resolve bets
            for player in self.players:
                self.resolve_bets(player, dealer_value, bet)

        msg = "Game over. Thanks for playing!"
        send_chat_msg(self._sio, msg)


if __name__ == "__main__":
    num_players = 2  # Set the desired number of players
    game = BlackjackBot(num_players=num_players)
    game.play()
