import logging
import os
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup as bs

from cytubebot.blackjack.blackjack_bot import BlackjackBot
from cytubebot.chatbot.processors.content import add_christmas_videos, content_handler
from cytubebot.chatbot.processors.random import random_handler
from cytubebot.chatbot.processors.tags import add_tags, remove_tags
from cytubebot.chatbot.processors.user_management import add_user, remove_user
from cytubebot.common.commands import Commands
from cytubebot.common.exceptions import InvalidTagError
from cytubebot.common.socket_extensions import send_chat_msg
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

        self._command_symbols = os.environ.get('COMMAND_SYMBOLS').split(',')

    def process_chat(self, chat_msg) -> None:
        user = chat_msg['username']
        command = chat_msg['msg'].split()[0].casefold()
        chat_ts = datetime.fromtimestamp(chat_msg['time'] / 1000)
        delta = datetime.now() - timedelta(seconds=10)

        if (
            (chat_ts < delta)
            or (user == os.getenv('CYTUBE_USERNAME'))
            or (not command[:1] in self._command_symbols)
        ):
            return
        else:
            command = command[1:]

        try:
            args = [x for x in chat_msg['msg'].split()[1:]]
        except IndexError:
            args = None

        if command in list(Commands.STANDARD_COMMANDS.value.keys()) or command in list(
            Commands.BLACKJACK_COMMANDS.value.keys()
        ):
            if command in list(Commands.STANDARD_COMMANDS.value.keys()):
                self._process_chat_command(user, command, args)
            elif command in list(Commands.BLACKJACK_COMMANDS.value.keys()):
                self._process_blackjack_chat_command(user, command, args)
        elif command in list(Commands.ADMIN_COMMANDS.value.keys()) or command in list(
            Commands.BLACKJACK_ADMIN_COMMANDS.value.keys()
        ):
            if self._sio_data.users.get(chat_msg['username'], 0) < 3:
                msg = 'You don\'t have permission to do that.'
                send_chat_msg(self._sio, msg)
                return

            if command in list(Commands.ADMIN_COMMANDS.value.keys()):
                self._process_chat_command(user, command, args, allow_force=True)
            elif command in list(Commands.BLACKJACK_ADMIN_COMMANDS.value.keys()):
                self._process_blackjack_chat_command(user, command, args)
        else:
            msg = f'{command} is not a valid command'
            send_chat_msg(self._sio, msg)

    def _process_chat_command(self, user, command, args, allow_force=False) -> None:
        if self._sio_data.lock and not (allow_force and args and args[0] == '--force'):
            msg = 'Already busy, please wait...'
            send_chat_msg(self._sio, msg)
        else:
            self._sio_data.lock = True
            self._process_command(user, command, args)
            self._sio_data.lock = False

    def _process_blackjack_chat_command(self, user, command, args) -> None:
        if self.blackjack_bot:
            self.blackjack_bot.process_command(user, command, args)
        else:
            msg = 'No blackjack games currently in progress.'
            send_chat_msg(self._sio, msg)

    def _process_command(self, user, command, args) -> None:
        match command:
            case 'content':
                if args:
                    tag = args[0].upper()
                else:
                    tag = None
                content_handler(
                    self._content_finder, tag, self._db, self._sio, self._sio_data
                )
            case 'random' | 'random_word':
                random_handler(
                    command, args, self._random_finder, self._sio, self._sio_data
                )
            case 'blackjack':
                if self.blackjack_bot:
                    msg = 'Blackjack game already in progress, try !join'
                    send_chat_msg(self._sio, msg)
                    return
                if args:
                    self.blackjack_bot = BlackjackBot(self._sio, user, args[0])
                else:
                    self.blackjack_bot = BlackjackBot(self._sio, user)
                msg = 'Starting blackjack, use !join to play.'
                send_chat_msg(self._sio, msg)
            case 'current':
                self._sio.emit('playerReady')
                curr = self._sio_data.current_media

                url = f'https://www.youtube.com/watch?v={curr["id"]}'
                resp = requests.get(url, timeout=60)
                page = resp.text
                soup = bs(page, 'lxml')
                ytInitialPlayerResponse = soup.find(
                    'script', string=re.compile('ytInitialPlayerResponse')
                )
                description = re.search(
                    '.*"description":{"simpleText":"(.*?)"',
                    ytInitialPlayerResponse.text,
                ).group(1)
                description = description.replace('\\n', ' ')

                curr['description'] = description
                self._logger.info(f'{curr=}')
                msg = f'{curr}'
                send_chat_msg(self._sio, msg)
            case 'add':
                add_user(args, self._db, self._sio)
            case 'remove':
                remove_user(args, self._db, self._sio)
            case 'add_tags' | 'remove_tags':
                try:
                    if command == 'add_tags':
                        add_tags(args, self._db)
                    else:
                        remove_tags(args, self._db)
                except IndexError:
                    msg = 'Not enough args supplied for !add_tags.'
                    send_chat_msg(self._sio, msg)
                except InvalidTagError:
                    msg = f'One or more tags in {args[1:]} is invalid.'
                    send_chat_msg(self._sio, msg)
            case 'christmas' | 'xmas':
                add_christmas_videos(self._sio)
            case 'help':
                msg = (
                    f'Use any of {self._command_symbols} with: '
                    f'{Commands.STANDARD_COMMANDS.value=}, '
                    f'{Commands.ADMIN_COMMANDS.value=}, '
                    f'{Commands.BLACKJACK_COMMANDS.value=}, '
                    f'{Commands.BLACKJACK_ADMIN_COMMANDS.value=}'
                )
                send_chat_msg(self._sio, msg)
            case 'kill':
                if self.blackjack_bot:
                    self.blackjack_bot.kill = True

                # Kill the DB container
                requests.get('http://postgres.content-finder:5000/shutdown', timeout=60)

                send_chat_msg(self._sio, 'Bye bye!')
                self._sio.sleep(3)  # temp sol to allow the chat msg to send
                self._sio.disconnect()
            case _:
                msg = f'Missing case for command {command}'
                send_chat_msg(self._sio, msg)
