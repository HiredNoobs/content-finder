import socketio
from cytubebot.blackjack.dealer import Dealer
from cytubebot.blackjack.player import Player


class BlackjackBot:
    commands = ['!join', '!bet', '!hit', '!split', '!hold']
    admin_commands = ['!start', '!stop_blackjack']

    def __init__(self, socket: socketio, player: str,
                 starting_chips: int = 1000) -> None:
        # Socket will be used as 'write' only i.e. the main bot will handle
        # all the main reading so that we don't process everything twice.
        self.sio = socket

        try:
            self.starting_chips = int(starting_chips)
        except ValueError:
            self.starting_chips = 1000

        msg = f'Starting chips for all players set to {self.starting_chips}'
        self.sio.emit('chatMsg', {'msg': msg})

        self.players = {
            player: Player(self.starting_chips)
        }
        self.dealer = Dealer()

        self.started = False
        self.bet_lock = False
        self.kill = False

    def process_command(self, user, command, args) -> None:
        match command:
            case '!join':
                if user in self.players.keys():
                    msg = f'Player {user} already playing.'
                    self.sio.emit('chatMsg', {'msg': msg})
                    return
                self.players[user] = Player(self.starting_chips)
                msg = f'Player {user} successfully joined.'
                self.sio.emit('chatMsg', {'msg': msg})
            case '!start':
                if self.started:
                    msg = ('Blackjack already in progress, use "!join" to play'
                           ' the next round.')
                    self.sio.emit('chatMsg', {'msg': msg})
                    return
                self.started = True
                self._play_blackjack()
            case '!bet':
                if not self.started:
                    msg = 'Blackjack not in progress...'
                    self.sio.emit('chatMsg', {'msg': msg})
                    return

                if self.bet_lock:
                    msg = 'You cannot bet right now.'
                    self.sio.emit('chatMsg', {'msg': msg})
                    return

                try:
                    bet = int(args[0])
                except (IndexError, ValueError):
                    msg = f'{user} - there was an error setting your bet, try again.'
                    self.sio.emit('chatMsg', {'msg': msg})
                    return

                self.players[user].bet = bet

                if self.players[user].error:
                    msg = f'{user} - there was an error setting your bet, try again.'
                    self.sio.emit('chatMsg', {'msg': msg})
            case '!hit':
                self.players[user].command = 'hit'
            case '!split':
                self.players[user].command = 'split'
            case '!hold':
                self.players[user].command = 'hold'
            case '!stop_blackjack':
                if not self.started:
                    msg = 'Blackjack not in progress...'
                    self.sio.emit('chatMsg', {'msg': msg})
                    return
                self.kill = True
                msg = 'Blackjack will end after this round.'
                self.sio.emit('chatMsg', {'msg': msg})
            case _:
                msg = f'Missing case for command {command}'
                self.sio.emit('chatMsg', {'msg': msg})

    def _play_blackjack(self) -> None:
        while True:
            if self.kill:
                self.kill = False
                self.started = False
                return
            if not self.players:
                msg = 'There are no players, stopping blackjack...'
                self.sio.emit('chatMsg', {'msg': msg})
                self.started = False
                return

            msg = 'Setting up for new round please wait.'
            self.sio.emit('chatMsg', {'msg': msg})

            # NEW ROUND SETUP
            self.dealer.reset()
            for player in self.players:
                self.players[player].reset()
            self.bet_lock = False

            # START NEW ROUND
            msg = 'Place your bets (30 secs).'
            self.sio.emit('chatMsg', {'msg': msg})

            self.sio.sleep(30)
            self.bet_lock = True

            # Give players & dealer their cards
            for i in range(0, 2):
                # NOTE: Since we're not using an ordered dict, this order
                # will be random every time.
                for player, player_obj in self.players.items():
                    card = self.dealer.get_card_from_deck()
                    player_obj.hand.append(card)
                    # msg = f'{player} gets {card}.'
                    # self.sio.emit('chatMsg', {'msg': msg})
                
                card = self.dealer.get_card_from_deck()
                self.dealer.hand.append(card)
                # msg = 'Dealer gets face down card.' if i == 0 else f'Dealer gets {card}.'
                # self.sio.emit('chatMsg', {'msg': msg})

            hand_art = self.dealer.get_hand_ascii()
            msg = f'Dealers hand:'
            self.sio.emit('chatMsg', {'msg': msg})
            for line in hand_art:
                self.sio.emit('chatMsg', {'msg': line})
                self.sio.sleep(0.25)

            if self.dealer.check_blackjack():
                msg = f'Dealer has blackjack with: {self.dealer.hand}'
                self.sio.emit('chatMsg', {'msg': msg})
                for player, player_obj in self.players.items():
                    msg = f'{player} loses {player_obj.bet}.'
                    self.sio.emit('chatMsg', {'msg': msg})
                    player_obj.chips -= player_obj.bet
                continue

            # Play the hand
            for player, player_obj in self.players.items():
                if player_obj.bet == 0:
                    continue

                hand_art = player_obj.get_hand_ascii()
                msg = f'{player}\'s hand:'
                self.sio.emit('chatMsg', {'msg': msg})
                for line in hand_art:
                    self.sio.emit('chatMsg', {'msg': line})
                    self.sio.sleep(0.25)

                if player_obj.check_blackjack():
                    msg = f'{player} has blackjack.'
                    self.sio.emit('chatMsg', {'msg': msg})
                    continue
                msg = f'{player} - your turn to play.'
                self.sio.emit('chatMsg', {'msg': msg})

                # Getting command(s) for player hand
                while True:
                    msg = f'{player} would you like to !hit, !split, or !hold.'
                    self.sio.emit('chatMsg', {'msg': msg})

                    # Waiting for player to give command
                    command = None
                    for _ in range(0, 60):
                        command = player_obj.command
                        if command:
                            break
                        self.sio.sleep(0.5)
                    
                    # Skip player if no command given
                    # TODO: Remove player if they continue to fail to play
                    if not player_obj.command:
                        msg = f'{player} did not give a command in time, skipping.'
                        self.sio.emit('chatMsg', {'msg': msg})
                        break
                    
                    match command:
                        case 'hit':
                            card = self.dealer.get_card_from_deck()
                            player_obj.hand.append(card)
                            msg = f'{player} gets {card}, current hand: {player_obj.hand}'
                            self.sio.emit('chatMsg', {'msg': msg})

                            if player_obj.check_blackjack():
                                msg = f'{player} has blackjack.'
                                self.sio.emit('chatMsg', {'msg': msg})
                                break
                            if player_obj.check_bust():
                                msg = f'{player} is bust.'
                                self.sio.emit('chatMsg', {'msg': msg})
                                break
                        case 'split':
                            # TODO: Remove player if they try multiple times
                            # when not available - this can currently be used
                            # to hold the game hostage
                            if not player_obj.check_split_available():
                                msg = 'Split not available'
                                self.sio.emit('chatMsg', {'msg': msg})
                                continue
                            # TODO: Add split func
                            msg = 'Split not yet implemented, sorry!'
                            self.sio.emit('chatMsg', {'msg': msg})
                        case 'hold':
                            break
                        case _:
                            pass
                player_obj.set_result()

            # Dealer players
            while True:
                if self.dealer.check_blackjack():
                    msg = f'Dealer has blackjack with: {self.dealer.hand}'
                    self.sio.emit('chatMsg', {'msg': msg})
                    break
                if self.dealer.check_bust():
                    msg = f'Dealer is bust with: {self.dealer.hand}'
                    self.sio.emit('chatMsg', {'msg': msg})
                    break
                if self.dealer.check_stand():
                    msg = f'Dealer must stand with: {self.dealer.hand}'
                    self.sio.emit('chatMsg', {'msg': msg})
                    break

                card = self.dealer.get_card_from_deck()
                self.dealer.hand.append(card)
                msg = f'Dealer gets {card}, current hand: {self.dealer.hand}'
                self.sio.emit('chatMsg', {'msg': msg})

            self.dealer.set_result()

            # Payout
            dealer_result = self.dealer.result  # either None or best numerical value of hand
            for player, player_obj in self.players.items():
                # Skip players who didn't bet
                if player_obj.bet == 0:
                    continue

                # Player & dealer bust
                if not player_obj.result and not dealer_result:
                    msg = f'{player} draws with dealer, nothing lost.'
                    self.sio.emit('chatMsg', {'msg': msg})
                # Player bust, dealer not
                elif not player_obj.result and dealer_result:
                    player_obj.chips -= player_obj.bet
                    msg = f'{player} loses {player_obj.bet}'
                    self.sio.emit('chatMsg', {'msg': msg})
                # Dealer bust, player not
                elif player_obj.result and not dealer_result:
                    player_obj.chips += player_obj.bet * 2
                    msg = f'{player} wins {player_obj.bet * 2}'
                    self.sio.emit('chatMsg', {'msg': msg})
                # Player & dealer blackjack
                elif player_obj.result == dealer_result:
                    msg = f'{player} draws with dealer, nothing lost.'
                    self.sio.emit('chatMsg', {'msg': msg})
                # Player blackjack, dealer less than
                elif player_obj.result == 21 and dealer_result < 21:
                    winnings = player_obj.bet * (player_obj.bet * 1.5)
                    player_obj.chips += winnings
                    msg = f'{player} wins {winnings}'
                    self.sio.emit('chatMsg', {'msg': msg})
                # player win
                elif player_obj.result > dealer_result:
                    player_obj.chips += player_obj.bet * 2
                    msg = f'{player} wins {player_obj.bet * 2}'
                    self.sio.emit('chatMsg', {'msg': msg})
                # Anything else should be a player loss
                else:
                    player_obj.chips -= player_obj.bet
                    msg = f'{player} loses {player_obj.bet}'
                    self.sio.emit('chatMsg', {'msg': msg})
