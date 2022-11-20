import socketio

from cytubebot.blackjack.dealer import Dealer
from cytubebot.blackjack.player import Player
from cytubebot.common.socket_extensions import send_chat_msg


class BlackjackBot:
    def __init__(
        self, socket: socketio, player: str, starting_chips: int = 1000
    ) -> None:
        # Socket will be used as 'write' only i.e. the main bot will handle
        # all the main reading so that we don't process everything twice.
        self._sio = socket

        try:
            self.starting_chips = int(starting_chips)
        except ValueError:
            self.starting_chips = 1000

        msg = f'Starting chips for all players set to {self.starting_chips}'
        send_chat_msg(self._sio, msg)

        self.players = {player: Player(self.starting_chips)}
        self.dealer = Dealer()

        self.started = False
        self.bet_lock = False
        self.kill = False

    def process_command(self, user, command, args) -> None:
        match command:
            case '!join':
                if user in self.players.keys():
                    msg = f'Player {user} already playing.'
                    send_chat_msg(self._sio, msg)
                    return
                self.players[user] = Player(self.starting_chips)
                msg = f'Player {user} successfully joined.'
                send_chat_msg(self._sio, msg)
            case '!start':
                if self.started:
                    msg = (
                        'Blackjack already in progress, use "!join" to play'
                        ' the next round.'
                    )
                    send_chat_msg(self._sio, msg)
                    return
                self.started = True
                self._play_blackjack()
            case '!bet':
                if not self.started:
                    msg = 'Blackjack not in progress...'
                    send_chat_msg(self._sio, msg)
                    return

                if self.bet_lock:
                    msg = 'You cannot bet right now.'
                    send_chat_msg(self._sio, msg)
                    return

                try:
                    bet = int(args[0])
                except (IndexError, ValueError):
                    msg = f'{user} - there was an error setting your bet, try again.'
                    send_chat_msg(self._sio, msg)
                    return

                self.players[user].bet = bet

                if self.players[user].error:
                    msg = f'{user} - there was an error setting your bet, try again.'
                    send_chat_msg(self._sio, msg)
            case '!hit':
                self.players[user].command = 'hit'
            case '!split':
                self.players[user].command = 'split'
            case '!hold':
                self.players[user].command = 'hold'
            case '!stop_blackjack':
                if not self.started:
                    msg = 'Blackjack not in progress...'
                    send_chat_msg(self._sio, msg)
                    return
                self.kill = True
                msg = 'Blackjack will end after this round.'
                send_chat_msg(self._sio, msg)
            case _:
                msg = f'Missing case for command {command}'
                send_chat_msg(self._sio, msg)

    def _play_blackjack(self) -> None:
        while True:
            if self.kill:
                self.kill = False
                self.started = False
                return
            if not self.players:
                msg = 'There are no players, stopping blackjack...'
                send_chat_msg(self._sio, msg)
                self.started = False
                return

            msg = 'Setting up for new round please wait.'
            send_chat_msg(self._sio, msg)

            # NEW ROUND SETUP
            self.dealer.reset()
            for player in self.players:
                self.players[player].reset()
            self.bet_lock = False

            # START NEW ROUND
            msg = 'Place your bets (30 secs).'
            send_chat_msg(self._sio, msg)

            self._sio.sleep(30)
            self.bet_lock = True

            # Give players & dealer their cards
            for i in range(0, 2):
                # NOTE: Since we're not using an ordered dict, this order
                # will be random every time.
                for player, player_obj in self.players.items():
                    card = self.dealer.get_card_from_deck()
                    player_obj.hand.append(card)

                card = self.dealer.get_card_from_deck()
                self.dealer.hand.append(card)

            hand_art = self.dealer.get_hand_ascii()
            msg = 'Dealers hand:'
            send_chat_msg(self._sio, msg)
            for line in hand_art:
                send_chat_msg(self._sio, line)
                self._sio.sleep(0.25)

            if self.dealer.check_blackjack():
                msg = f'Dealer has blackjack with: {self.dealer.hand}'
                send_chat_msg(self._sio, msg)
                for player, player_obj in self.players.items():
                    msg = f'{player} loses {player_obj.bet}.'
                    send_chat_msg(self._sio, msg)
                    player_obj.chips -= player_obj.bet
                continue

            # Play the hand
            for player, player_obj in self.players.items():
                if player_obj.bet == 0:
                    continue

                hand_art = player_obj.get_hand_ascii()
                msg = f'{player}\'s hand:'
                send_chat_msg(self._sio, msg)
                for line in hand_art:
                    send_chat_msg(self._sio, line)
                    self._sio.sleep(0.25)

                if player_obj.check_blackjack():
                    msg = f'{player} has blackjack.'
                    send_chat_msg(self._sio, msg)
                    continue
                msg = f'{player} - your turn to play.'
                send_chat_msg(self._sio, msg)

                # Getting command(s) for player hand
                while True:
                    msg = f'{player} would you like to !hit, !split, or !hold.'
                    send_chat_msg(self._sio, msg)

                    # Waiting for player to give command
                    command = None
                    for _ in range(0, 60):
                        command = player_obj.command
                        if command:
                            break
                        self._sio.sleep(0.5)

                    # Skip player if no command given
                    # TODO: Remove player if they continue to fail to play
                    if not player_obj.command:
                        msg = f'{player} did not give a command in time, skipping.'
                        send_chat_msg(self._sio, msg)
                        break

                    match command:
                        case 'hit':
                            card = self.dealer.get_card_from_deck()
                            player_obj.hand.append(card)
                            msg = (
                                f'{player} gets {card}, current hand: {player_obj.hand}'
                            )
                            send_chat_msg(self._sio, msg)

                            if player_obj.check_blackjack():
                                msg = f'{player} has blackjack.'
                                send_chat_msg(self._sio, msg)
                                break
                            if player_obj.check_bust():
                                msg = f'{player} is bust.'
                                send_chat_msg(self._sio, msg)
                                break
                        case 'split':
                            # TODO: Remove player if they try multiple times
                            # when not available - this can currently be used
                            # to hold the game hostage
                            if not player_obj.check_split_available():
                                msg = 'Split not available'
                                send_chat_msg(self._sio, msg)
                                continue
                            # TODO: Add split func
                            msg = 'Split not yet implemented, sorry!'
                            send_chat_msg(self._sio, msg)
                        case 'hold':
                            break
                        case _:
                            pass
                player_obj.set_result()

            # Dealer players
            while True:
                if self.dealer.check_blackjack():
                    msg = f'Dealer has blackjack with: {self.dealer.hand}'
                    send_chat_msg(self._sio, msg)
                    break
                if self.dealer.check_bust():
                    msg = f'Dealer is bust with: {self.dealer.hand}'
                    send_chat_msg(self._sio, msg)
                    break
                if self.dealer.check_stand():
                    msg = f'Dealer must stand with: {self.dealer.hand}'
                    send_chat_msg(self._sio, msg)
                    break

                card = self.dealer.get_card_from_deck()
                self.dealer.hand.append(card)
                msg = f'Dealer gets {card}, current hand: {self.dealer.hand}'
                send_chat_msg(self._sio, msg)

            self.dealer.set_result()

            # Payout
            dealer_result = (
                self.dealer.result
            )  # either None or best numerical value of hand
            for player, player_obj in self.players.items():
                # Skip players who didn't bet
                if player_obj.bet == 0:
                    continue

                # Player & dealer bust
                if not player_obj.result and not dealer_result:
                    msg = f'{player} draws with dealer, nothing lost.'
                    send_chat_msg(self._sio, msg)
                # Player bust, dealer not
                elif not player_obj.result and dealer_result:
                    player_obj.chips -= player_obj.bet
                    msg = f'{player} loses {player_obj.bet}'
                    send_chat_msg(self._sio, msg)
                # Dealer bust, player not
                elif player_obj.result and not dealer_result:
                    player_obj.chips += player_obj.bet * 2
                    msg = f'{player} wins {player_obj.bet * 2}'
                    send_chat_msg(self._sio, msg)
                # Player & dealer blackjack
                elif player_obj.result == dealer_result:
                    msg = f'{player} draws with dealer, nothing lost.'
                    send_chat_msg(self._sio, msg)
                # Player blackjack, dealer less than
                elif player_obj.result == 21 and dealer_result < 21:
                    winnings = player_obj.bet * (player_obj.bet * 1.5)
                    player_obj.chips += winnings
                    msg = f'{player} wins {winnings}'
                    send_chat_msg(self._sio, msg)
                # player win
                elif player_obj.result > dealer_result:
                    player_obj.chips += player_obj.bet * 2
                    msg = f'{player} wins {player_obj.bet * 2}'
                    send_chat_msg(self._sio, msg)
                # Anything else should be a player loss
                else:
                    player_obj.chips -= player_obj.bet
                    msg = f'{player} loses {player_obj.bet}'
                    send_chat_msg(self._sio, msg)
