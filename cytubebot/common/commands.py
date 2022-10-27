from enum import Enum


class Commands(Enum):
    STANDARD_COMMANDS = ['!help']
    ADMIN_COMMANDS = [
        '!content',
        '!random',
        '!random_word',
        '!blackjack',
        '!kill',
        '!add',
        '!remove',
    ]

    BLACKJACK_COMMANDS = ['!join', '!bet', '!hit', '!split', '!hold']
    BLACKJACK_ADMIN_COMMANDS = ['!start', '!stop_blackjack']
