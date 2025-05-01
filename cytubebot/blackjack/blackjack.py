from typing import Dict, List

from cytubebot.blackjack.deck import Deck
from cytubebot.blackjack.player import Player


class BlackjackGame:
    def __init__(self) -> None:
        self.deck: Deck = Deck()
        self.dealer_hand: List[Dict[str, str]] = []
        self.players: Dict[str, Player] = {}
        # The game state can be one of: "idle", "joining", "betting", "playing"
        self.state: str = "idle"

    def add_player(self, username: str, initial_balance: int = 100) -> None:
        if username not in self.players:
            self.players[username] = Player(username, initial_balance)

    def start_round(self) -> None:
        if not self.players:
            raise Exception("No players to start the round.")

        self.deck = Deck()  # Start with a fresh deck.
        self.dealer_hand = []
        self.state = "playing"
        # Deal initial cards in two rounds.
        for _ in range(2):
            for player in self.players.values():
                # If the player hasn’t split, use the single hand.
                if player.hands is None:
                    player.hand.append(self.deck.draw_card())
                else:
                    player.add_card_to_active_hand(self.deck.draw_card())
            self.dealer_hand.append(self.deck.draw_card())

    def dealer_play(self) -> None:
        while self.calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.draw_card())

    def calculate_hand_value(self, hand: List[Dict[str, str]]) -> int:
        value = 0
        num_aces = 0
        for card in hand:
            rank = card["rank"]
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                num_aces += 1
            else:
                value += int(rank)
        for _ in range(num_aces):
            value += 11 if value + 11 <= 21 else 1
        return value

    def resolve_round(self, send_message_fn) -> None:
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        send_message_fn(f"Dealer's hand: {self.dealer_hand} (Value: {dealer_value})")
        for player in self.players.values():
            # If the player has split, evaluate each hand separately.
            if player.hands is None:
                hands_to_evaluate = [player.hand]
            else:
                hands_to_evaluate = player.hands

            for hand in hands_to_evaluate:
                player_value = player.calculate_hand_value(hand)
                bet = player.bet

                if player_value > 21:
                    send_message_fn(f"{player.name} busts on hand {hand}! You lose.")
                    player.balance -= bet
                elif dealer_value > 21 or dealer_value < player_value:
                    send_message_fn(
                        f"{player.name} wins on hand {hand}! You win {bet} chips."
                    )
                    player.balance += bet
                elif dealer_value == player_value:
                    send_message_fn(
                        f"{player.name}, it's a tie on hand {hand}! {bet} is returned."
                    )
                else:
                    send_message_fn(
                        f"{player.name}, dealer wins against hand {hand}. You lose {bet}."
                    )
                    player.balance -= bet

        # Prepare for the next round.
        for player in self.players.values():
            player.reset_hands()
        self.dealer_hand = []
        self.state = "joining"
        send_message_fn(
            "Round over. Use 'join' to enter the game or 'start_blackjack' to start a new round."
        )

    def all_players_done(self) -> bool:
        return all(player.finished for player in self.players.values())

    def place_bet(self, username: str, bet_str: str, send_message_fn) -> None:
        player = self.players.get(username)
        if not player:
            send_message_fn(f"Player {username} not found.")
            return
        try:
            bet_amount = int(bet_str)
            if bet_amount <= 0 or bet_amount > player.balance:
                send_message_fn("Invalid bet. Please enter a valid amount.")
            else:
                player.bet = bet_amount
                send_message_fn(f"{username} bet set to {bet_amount}.")
        except ValueError:
            send_message_fn("Invalid input. Please enter a valid integer bet.")
