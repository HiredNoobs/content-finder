from enum import Enum


class Commands(Enum):
    STANDARD_COMMANDS = ['!help']
    ADMIN_COMMANDS = [
        '!add',
        '!add_tags',
        '!blackjack',
        '!content',
        '!kill',
        '!random',
        '!random_word',
        '!remove',
        '!remove_tags',
    ]

    BLACKJACK_COMMANDS = ['!bet', '!hit', '!hold', '!join', '!split']
    BLACKJACK_ADMIN_COMMANDS = ['!start', '!stop_blackjack']
