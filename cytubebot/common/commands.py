from enum import Enum


class Commands(Enum):
    STANDARD_COMMANDS = {'help': 'Prints out all commands.'}
    ADMIN_COMMANDS = {
        'add': 'Add channel to database, use channel username, ID, or URL.',
        'add_tags': '',
        'blackjack': '',
        'content': '',
        'current': '',
        'christmas': '',
        'kill': '',
        'random': '',
        'random_word': '',
        'remove': '',
        'remove_tags': '',
        'xmas': '',
    }

    BLACKJACK_COMMANDS = {
        'bet': '',
        'hit': '',
        'hold': '',
        'join': '',
        'split': '',
    }
    BLACKJACK_ADMIN_COMMANDS = {'start': '', 'stop_blackjack': ''}
