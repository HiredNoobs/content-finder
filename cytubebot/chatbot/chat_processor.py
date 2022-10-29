import logging
import os
from datetime import datetime, timedelta

import requests

from cytubebot.blackjack.blackjack_bot import BlackjackBot
from cytubebot.chatbot.processors.content import content_handler
from cytubebot.chatbot.processors.random import random_handler
from cytubebot.chatbot.processors.tags import add_tags, remove_tags
from cytubebot.chatbot.processors.user_management import add_user, remove_user
from cytubebot.common.commands import Commands
from cytubebot.common.exceptions import InvalidTagError
from cytubebot.contentfinder.content_finder import ContentFinder
from cytubebot.contentfinder.database import DBHandler
from cytubebot.randomvideo.random_finder import RandomFinder


class ChatProcessor:
    def __init__(self, sio, sio_data) -> None:
        self._logger = logging.getLogger(__name__)

        self._sio = sio  # A reference to the SocketIO client held in ChatBot
        self._sio_data = sio_data

        self.blackjack_bot = None
        self._db = DBHandler()
        self._random_finder = RandomFinder()
        self._content_finder = ContentFinder()

    def process_chat(self, chat_msg) -> None:
        user = chat_msg['username']
        command = chat_msg['msg'].split()[0].casefold()
        chat_ts = datetime.fromtimestamp(chat_msg['time'] / 1000)
        delta = datetime.now() - timedelta(seconds=10)

        if (
            (chat_ts < delta)
            or (user == os.getenv('CYTUBE_USERNAME'))
            or (not command[:1] == '!')
        ):
            return

        try:
            args = [x for x in chat_msg['msg'].split()[1:]]
        except IndexError:
            args = None

        if (
            command in Commands.STANDARD_COMMANDS.value
            or command in Commands.BLACKJACK_COMMANDS.value
        ):
            if command in Commands.STANDARD_COMMANDS.value:
                self._process_chat_command(user, command, args)
            elif command in Commands.BLACKJACK_COMMANDS.value:
                self._process_blackjack_chat_command(user, command, args)
        elif (
            command in Commands.ADMIN_COMMANDS.value
            or command in Commands.BLACKJACK_ADMIN_COMMANDS.value
        ):
            if self._sio_data.users.get(chat_msg['username'], 0) < 3:
                msg = 'You don\'t have permission to do that.'
                self._sio.emit('chatMsg', {'msg': msg})
                return

            if command in Commands.ADMIN_COMMANDS.value:
                self._process_chat_command(user, command, args, allow_force=True)
            elif command in Commands.BLACKJACK_ADMIN_COMMANDS.value:
                self._process_blackjack_chat_command(user, command, args)
        else:
            msg = f'{command} is not a valid command'
            self._sio.emit('chatMsg', {'msg': msg})

    def _process_chat_command(self, user, command, args, allow_force=False) -> None:
        if self._sio_data.lock and not (allow_force and args and args[0] == '--force'):
            msg = 'Already busy, please wait...'
            self._sio.emit('chatMsg', {'msg': msg})
        else:
            self._sio_data.lock = True
            self._process_command(user, command, args)
            self._sio_data.lock = False

    def _process_blackjack_chat_command(self, user, command, args) -> None:
        if self.blackjack_bot:
            self.blackjack_bot.process_command(user, command, args)
        else:
            msg = 'No blackjack games currently in progress.'
            self._sio.emit('chatMsg', {'msg': msg})

    def _process_command(self, user, command, args) -> None:
        match command:
            case '!content':
                if args:
                    tag = args[0].upper()
                else:
                    tag = None
                content_handler(
                    self._content_finder, tag, self._db, self._sio, self._sio_data
                )
            case '!random' | '!random_word':
                random_handler(
                    command, args, self._random_finder, self._sio, self._sio_data
                )
            case '!blackjack':
                if self.blackjack_bot:
                    msg = 'Blackjack game already in progress, try !join'
                    self._sio.emit('chatMsg', {'msg': msg})
                    return
                if args:
                    self.blackjack_bot = BlackjackBot(self._sio, user, args[0])
                else:
                    self.blackjack_bot = BlackjackBot(self._sio, user)
                msg = 'Starting blackjack, use !join to play.'
                self._sio.emit('chatMsg', {'msg': msg})
            case '!add':
                add_user(args, self._db, self._sio)
            case '!remove':
                remove_user(args, self._db, self._sio)
            case '!add_tags' | '!remove_tags':
                try:
                    if command == '!add_tags':
                        add_tags(args, self._db)
                    else:
                        remove_tags(args, self._db)
                except IndexError:
                    msg = 'Not enough args supplied for !add_tags.'
                    self._sio.emit('chatMsg', {'msg': msg})
                except InvalidTagError:
                    msg = f'One or more tags in {args[1:]} is invalid.'
                    self._sio.emit('chatMsg', {'msg': msg})
            case '!help':
                msg = (
                    f'Standard commands: {Commands.STANDARD_COMMANDS.value}'
                    f', Admin commands: {Commands.ADMIN_COMMANDS.value}'
                    f', blackjack commands: {Commands.BLACKJACK_COMMANDS.value}'
                    f', blackjack admin commmands: {Commands.BLACKJACK_ADMIN_COMMANDS.value}'
                )
                self._sio.emit('chatMsg', {'msg': msg})
            case '!kill':
                if self.blackjack_bot:
                    self.blackjack_bot.kill = True

                # Kill the DB container
                requests.get('http://postgres.content-finder:5000/shutdown', timeout=60)

                self._sio.emit('chatMsg', {'msg': 'Bye bye!'})
                self._sio.sleep(3)  # temp sol to allow the chat msg to send
                self._sio.disconnect()
            case _:
                msg = f'Missing case for command {command}'
                self._sio.emit('chatMsg', {'msg': msg})
