import random
import socketio

from cytubebot.common.socket_extensions import send_chat_msg


class BlackjackBot:
    def __init__(self, socket: socketio, num_players=1, initial_balance=100):
        # Socket will be used as 'write' only i.e. the main bot will handle
        # all the main reading so that we don't process everything twice.
        self._sio = socket
        # self.num_players = num_players
        # self.players = [self.create_player(initial_balance) for _ in range(num_players)]
        self.deck = None
        self.dealer_hand = None
        self.players = None

        self.in_progress = False
        self.can_join = False
        self.betting_allowed = False
        self.round_over = False

    def process_chat_command(self, username, command, args) -> None:
        match command:
            case 'init_blackjack':
                if not self.in_progress:
                    msg = 'Initialising blackjack, use join to enter the game. The game will start when an admin runs start_blackjack. Set your bets with bet'
                    send_chat_msg(self._sio, msg)
                    self.in_progress = True
                    self.can_join = True
                    self.betting_allowed = True
                    self.players = {}
            case 'start_blackjack':
                msg = 'No players, not starting...'
                if not self.players:
                    send_chat_msg(self._sio, msg)
                    return

                # self.in_progress = True
                self.can_join = False
                self.betting_allowed = False
                self.round_over = False
                self.deck = self.create_deck()
                self.dealer_hand = []

                # Deal initial cards
                for _ in range(2):
                    for player in self.players.keys():
                        self.deal_card(self.players[player]['hand'])
                    self.deal_card(self.dealer_hand)

                msg = f'Dealer\'s first card is: {self.dealer_hand[0]}'
                send_chat_msg(self._sio, msg)

                for player, player_data in self.players.items():
                    msg = f"{player}, your hand: {player_data['hand']} (Value: {self.calculate_hand_value(player_data['hand'])})"
                    send_chat_msg(self._sio, msg)
            case 'join':
                if self.can_join and username not in self.players.keys():
                    self.create_player(username)
                    msg = f'{username} successfully joined blackjack!'
                    send_chat_msg(self._sio, msg)
            case 'bet':
                if username in self.players.keys() and self.betting_allowed:
                    self.place_bet(username, args[0])
            case 'hit':
                if self.in_progress and username in self.players.keys() and not self.players[username]['finished'] and not self.betting_allowed:
                    self.deal_card(self.players[username]['hand'])

                    msg = f"{username}, your hand: {self.players[username]['hand']} (Value: {self.calculate_hand_value(self.players[username]['hand'])})"
                    send_chat_msg(self._sio, msg)

                    player_value = self.calculate_hand_value(self.players[username]['hand'])
                    if player_value > 21:
                        msg = f"{username} busts! You lose."
                        send_chat_msg(self._sio, msg)
                        self.players[username]['finished'] = True
                    elif player_value == 21:
                        msg = f"{username} has blackjack!"
                        send_chat_msg(self._sio, msg)
                        self.players[username]['finished'] = True
            case 'stand':
                if self.in_progress and username in self.players.keys() and not self.players[username]['finished'] and not self.betting_allowed:
                    self.players[username]['finished'] = True
                    msg = f'{username} is standing.'
                    send_chat_msg(self._sio, msg)
            case 'stop_blackjack':
                self.in_progress = False
                self.can_join = False
                self.betting_allowed = False
                self.round_over = False
                self.deck = None
                self.dealer_hand = None
                self.players = None
                msg = 'Stopping blackjack.'
                send_chat_msg(self._sio, msg)

        # While a game is in progress, after every command we'll check
        # if the game is effectively over and then we'll finish the game.
        if self.in_progress and not self.round_over and self.players and all(player_data['finished'] for player_data in self.players.values()):
            self.round_over = True
            msg = f'Dealer\'s hand: {self.dealer_hand}.'
            send_chat_msg(self._sio, msg)
            # Dealer's turn
            while self.calculate_hand_value(self.dealer_hand) < 17:
                self.deal_card(self.dealer_hand)
            dealer_value = self.calculate_hand_value(self.dealer_hand)
            msg = f"Dealer's hand: {self.dealer_hand} (Value: {dealer_value})"
            send_chat_msg(self._sio, msg)

            # Resolve bets
            for player, player_data in self.players.items():
                self.resolve_bets(player, dealer_value, player_data['bet'])

            # Setup the next round
            for player in self.players:
                self.players[player] = {
                    'hand': [],
                    'split_hand': [],
                    'balance': self.players[player]['balance'],
                    'bet': 0,
                    'finished': False
                }

            msg = 'Round over! Betting is open. An admin can start the next round with start_blackjack.'
            send_chat_msg(self._sio, msg)

            self.can_join = True
            self.betting_allowed = True

    def create_player(self, username, initial_balance=100):
        self.players[username] = {
            'hand': [],
            'split_hand': [],
            'balance': initial_balance,
            'bet': 0,
            'finished': False
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

    def place_bet(self, player, bet):
        """Place a bet for a player."""
        try:
            bet = int(bet)
            if bet <= 0 or bet > self.players[player]['balance']:
                msg = "Invalid bet. Please enter a valid amount."
                send_chat_msg(self._sio, msg)
            else:
                msg = f'{player} bet set to {bet}.'
                send_chat_msg(self._sio, msg)
                self.players[player]['bet'] = bet
        except ValueError:
            msg = "Invalid input. Please enter a valid integer."
            send_chat_msg(self._sio, msg)

    # def split(self, player):
    #     """Split a player's hand into two separate hands."""
    #     if len(player['hand']) == 2 and player['hand'][0]['rank'] == player['hand'][1]['rank']:
    #         player['split_hand'].append([player['hand'].pop(), self.deck.pop()])
    #         player['hand'].append(self.deck.pop())
    #         msg = f"Player {self.players.index(player) + 1} has split their hand!"
    #         send_chat_msg(self._sio, msg)

    # def double_down(self, player, bet):
    #     """Double down a player's bet and deal one more card."""
    #     if len(player['hand']) == 2:
    #         player['balance'] -= bet
    #         self.deal_card(player['hand'])
    #         msg = f"Player {self.players.index(player) + 1} has doubled down!"
    #         send_chat_msg(self._sio, msg)

    def resolve_bets(self, player, dealer_value, bet):
        """Resolve bets for a player based on hand values."""
        hand_value = self.calculate_hand_value(self.players[player]['hand'])
        if hand_value > 21:
            msg = f"{player} busts! You lose."
            send_chat_msg(self._sio, msg)
            self.players[player]['balance'] -= bet
        elif dealer_value > 21 or dealer_value < hand_value:
            msg = f"{player} wins! You won {bet} chips."
            send_chat_msg(self._sio, msg)
            self.players[player]['balance'] += 2 * bet
        elif dealer_value == hand_value:
            msg = f"{player}, it's a tie! Your bet is returned."
            send_chat_msg(self._sio, msg)
            self.players[player]['balance'] += bet
        else:
            msg = f"{player}, dealer wins. You lose your bet."
            send_chat_msg(self._sio, msg)

    # def play(self):
    #     """Play the multi-player blackjack game."""
    #     msg = "Starting Blackjack!"
    #     send_chat_msg(self._sio, msg)

    #     # Deal initial cards
    #     for _ in range(2):
    #         for player in self.players:
    #             self.deal_card(player['hand'])
    #         self.deal_card(self.dealer_hand)

    #     while any(player['balance'] > 0 for player in self.players):
    #         self.dealer_hand = []
    #         for player in self.players:
    #             bet = self.place_bet(player)
    #             self.player_action(player, bet)
    #             if player['split_hand']:
    #                 msg = 'SPLIT HAND ROUND'
    #                 send_chat_msg(self._sio, msg)
    #                 player['hand'] = player['split_hand']
    #                 self.player_action(player, bet)

    #         # Dealer's turn
    #         while self.calculate_hand_value(self.dealer_hand) < 17:
    #             self.deal_card(self.dealer_hand)
    #         dealer_value = self.calculate_hand_value(self.dealer_hand)
    #         msg = f"Dealer's hand: {self.dealer_hand} (Value: {dealer_value})"
    #         send_chat_msg(self._sio, msg)

    #         # Resolve bets
    #         for player in self.players:
    #             self.resolve_bets(player, dealer_value, bet)

    #     msg = "Game over. Thanks for playing!"
    #     send_chat_msg(self._sio, msg)


if __name__ == "__main__":
    num_players = 2  # Set the desired number of players
    game = BlackjackBot(num_players=num_players)
    game.play()
