import os
from enum import Enum


class Commands(Enum):
    COMMAND_SYMBOLS = os.environ.get("COMMAND_SYMBOLS").split(",")

    STANDARD_COMMANDS = {"help": "Prints out all commands."}

    ADMIN_COMMANDS = {
        "add": "Add channel to database, use channel username, ID, or URL.",
        "add_tags": "",
        "content": "",
        "current": "",
        "christmas": "",
        "kill": "",
        "random": "",
        "random_word": "",
        "remove": "",
        "remove_tags": "",
        "xmas": "",
    }

    BLACKJACK_COMMANDS = {
        "bet": "",
        "hit": "",
        "hold": "",
        "join": "",
        "split": "",
        "double": "",
        "stand": "",
    }

    BLACKJACK_ADMIN_COMMANDS = {
        "init_blackjack": "",
        "start_blackjack": "",
        "stop_blackjack": "",
    }
