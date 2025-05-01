import logging
from typing import Any, List

from cytubebot.blackjack.blackjack import BlackjackGame
from cytubebot.common.socket_extensions import send_chat_msg


class BlackjackBot:
    def __init__(self, sio: Any) -> None:
        self._sio = sio  # The socket instance for emitting chat messages.
        self.blackjack = BlackjackGame()
        self._logger = logging.getLogger(__name__)

    def process_chat_command(
        self, username: str, command: str, args: List[str]
    ) -> None:
        self._logger.debug(f"Processing blackjack command {command=}, {args=}")
        match command:
            case "init_blackjack":
                self._handle_init_blackjack()
            case "join":
                self._handle_join(username)
            case "bet":
                self._handle_bet(username, args)
            case "start_blackjack":
                self._handle_start_blackjack()
            case "hit":
                self._handle_hit(username)
            case "stand":
                self._handle_stand(username)
            case "split":
                self._handle_split(username)
            case "stop_blackjack":
                self._handle_stop_blackjack()
            case _:
                send_chat_msg(self._sio, f"Unknown blackjack command: {command}")

        # After every command, if the game is in play and all players have finished, resolve the round.
        if self.blackjack.state == "playing" and self.blackjack.all_players_done():
            self._handle_end_round()

    def _handle_init_blackjack(self) -> None:
        self.blackjack = BlackjackGame()
        self.blackjack.state = "joining"
        send_chat_msg(self._sio, "Blackjack initialized. Use 'join' to enter the game.")

    def _handle_join(self, username: str) -> None:
        if self.blackjack.state == "joining":
            self.blackjack.add_player(username)
            send_chat_msg(self._sio, f"{username} joined blackjack!")
        else:
            send_chat_msg(self._sio, "Cannot join at this time.")

    def _handle_bet(self, username: str, args: List[str]) -> None:
        if self.blackjack.state == "joining" and username in self.blackjack.players:
            if not args:
                send_chat_msg(self._sio, "Please specify a bet amount.")
                return
            self.blackjack.place_bet(
                username, args[0], lambda msg: send_chat_msg(self._sio, msg)
            )
        else:
            send_chat_msg(self._sio, "Betting not allowed at this time.")

    def _handle_start_blackjack(self) -> None:
        if self.blackjack.state != "joining":
            self._logger.debug(
                f"{self.blackjack.state} not one of joining, game not starting."
            )
            return

        if any(player.bet == 0 for player in self.blackjack.players.values()):
            send_chat_msg(self._sio, "Missing bets from players.")
            return

        try:
            self.blackjack.start_round()
            send_chat_msg(
                self._sio,
                f"Dealer's first card is: {self.blackjack.dealer_hand[0]}",
            )
            for player in self.blackjack.players.values():
                if player.hands is None:
                    hv = player.calculate_hand_value(player.hand)
                    send_chat_msg(
                        self._sio,
                        f"{player.name}, your hand: {player.hand} (Value: {hv})",
                    )
                else:
                    hv = player.calculate_active_hand_value()
                    send_chat_msg(
                        self._sio,
                        f"{player.name}, active hand: {player.get_active_hand()} (Value: {hv})",
                    )
        except Exception as e:
            send_chat_msg(self._sio, f"Error starting round: {e}")

    def _handle_hit(self, username: str) -> None:
        if self.blackjack.state == "playing" and username in self.blackjack.players:
            player = self.blackjack.players[username]
            if not player.finished:
                try:
                    card = self.blackjack.deck.draw_card()
                except Exception as e:
                    send_chat_msg(self._sio, f"Error drawing card: {e}")
                    return
                player.add_card_to_active_hand(card)
                active_hand = player.get_active_hand()
                hand_value = player.calculate_hand_value(active_hand)
                send_chat_msg(
                    self._sio,
                    f"{username}, your current hand: {active_hand} (Value: {hand_value})",
                )
                if hand_value > 21:
                    send_chat_msg(self._sio, f"{username} busts on this hand!")
                    player.finish_active_hand()
                elif hand_value == 21:
                    send_chat_msg(self._sio, f"{username} got Blackjack on this hand!")
                    player.finish_active_hand()
        else:
            send_chat_msg(self._sio, "Hit not allowed at this time.")

    def _handle_stand(self, username: str) -> None:
        if self.blackjack.state == "playing" and username in self.blackjack.players:
            self.blackjack.players[username].finish_active_hand()
            send_chat_msg(self._sio, f"{username} stands on the current hand.")
        else:
            send_chat_msg(self._sio, "Stand not allowed at this time.")

    def _handle_split(self, username: str) -> None:
        if self.blackjack.state != "playing":
            send_chat_msg(self._sio, "Can only split during play.")
            return
        player = self.blackjack.players.get(username)
        if not player:
            send_chat_msg(self._sio, f"Player {username} not found.")
            return
        if not player.can_split():
            send_chat_msg(
                self._sio,
                "Current hand cannot be split (must be exactly two cards with the same rank).",
            )
            return
        try:
            if player.do_split(self.blackjack.deck):
                send_chat_msg(self._sio, f"{username} has split the hand!")
                send_chat_msg(
                    self._sio, f"Now playing hand: {player.get_active_hand()}"
                )
            else:
                send_chat_msg(self._sio, "Error during splitting the hand.")
        except Exception as e:
            send_chat_msg(self._sio, f"Error splitting hand: {e}")

    def _handle_stop_blackjack(self) -> None:
        self.blackjack.state = "idle"
        self.blackjack.players = {}
        self.blackjack.dealer_hand = []
        send_chat_msg(self._sio, "Blackjack stopped.")

    def _handle_end_round(self) -> None:
        self.blackjack.dealer_play()
        dealer_value = self.blackjack.calculate_hand_value(self.blackjack.dealer_hand)
        send_chat_msg(
            self._sio,
            f"Dealer's hand: {self.blackjack.dealer_hand} (Value: {dealer_value})",
        )
        self.blackjack.resolve_round(lambda msg: send_chat_msg(self._sio, msg))
