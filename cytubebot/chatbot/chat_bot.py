import logging
import os

from datetime import datetime, timedelta

import requests
import socketio

from cytubebot.blackjack.blackjack_bot import BlackjackBot
from cytubebot.chatbot.chat_processor import ChatProcessor
from cytubebot.common.commands import Commands
from cytubebot.chatbot.sio_data import SIOData
from cytubebot.common.socket_extensions import send_chat_msg


class ChatBot:
    """
    The ChatBot class is a socketio wrapper that handles **only** the socket
    side of the chat bot and basic processing, any specific processing
    should be passed to the relevant class.
    """

    def __init__(
        self, url: str, channel_name: str, username: str, password: str
    ) -> None:
        self._logger = logging.getLogger(__name__)

        self.url = url
        self.channel_name = channel_name
        self.username = username
        self.password = password

        self._sio = socketio.Client()  # For debugging: engineio_logger=True
        self._sio_data = SIOData()
        self._chat_processor = ChatProcessor(self._sio, self._sio_data)
        self._blackjack_processor = BlackjackBot(self._sio)

    def _init_socket(self) -> str:
        """
        Finds the socket conn for channel given in .env - this method does NOT
        connect.

        returns:
            A str containing the url of the socket server.
        """
        socket_conf = f'{self.url}socketconfig/{self.channel_name}.json'
        resp = requests.get(socket_conf, timeout=60)
        self._logger.info(f'resp: {resp.status_code} - {resp.reason}')
        servers = resp.json()
        socket_url = ''

        for server in servers['servers']:
            if server['secure']:
                socket_url = server['url']
                break

        if not socket_url:
            raise socketio.exceptions.ConnectionError(
                'Unable to find a secure socket to connect to'
            )

        return socket_url

    def listen(self) -> None:
        """
        Main 'loop', connects to the socket server from _init_socket() and
        waits for chat commands.
        """

        @self._sio.event
        def connect():
            self._logger.info('Socket connected!')
            self._sio.emit('joinChannel', {'name': self.channel_name})

        @self._sio.on('channelOpts')
        def channel_opts(resp):
            self._logger.info(resp)
            self._sio.emit('login', {'name': self.username, 'pw': self.password})

        @self._sio.on('login')
        def login(resp):
            self._logger.info(resp)
            send_chat_msg(self._sio, 'Hello!')

        @self._sio.on('userlist')
        def userlist(resp):
            for user in resp:
                self._sio_data.users[user['name']] = user['rank']

        @self._sio.on('addUser')  # User joins channel
        @self._sio.on('setUserRank')
        def user_add(resp):
            self._sio_data.users[resp['name']] = resp['rank']

        @self._sio.on('userLeave')
        def user_leave(resp):
            self._sio_data.users.pop(resp['name'], None)

        @self._sio.on('chatMsg')
        def chat(resp):
            self._logger.info(resp)

            username = resp['username']
            command = resp['msg'].split()[0].casefold()
            chat_ts = datetime.fromtimestamp(resp['time'] / 1000)
            delta = datetime.now() - timedelta(seconds=10)

            # Check if the message is recent, or from the bot, or isn't a command
            if (
                (chat_ts < delta)
                or (username == os.getenv('CYTUBE_USERNAME'))
                or (not command[:1] in Commands.COMMAND_SYMBOLS.value)
            ):
                return

            command = command[1:]  # strip the command symbol
            try:
                args = [x for x in resp['msg'].split()[1:]]
            except IndexError:
                args = None

            if command in list(Commands.STANDARD_COMMANDS.value.keys()) or command in list(Commands.ADMIN_COMMANDS.value.keys()):
                if command in list(Commands.ADMIN_COMMANDS.value.keys()):
                    if self._sio_data.users.get(username, 0) < 3:
                        msg = 'You don\'t have permission to do that.'
                        send_chat_msg(self._sio, msg)
                    else:
                        self._chat_processor.process_chat_command(username, command, args, allow_force=True)
                else:
                    self._chat_processor.process_chat_command(username, command, args)
            elif command in list(Commands.BLACKJACK_COMMANDS.value.keys()) or command in list(Commands.BLACKJACK_ADMIN_COMMANDS.value.keys()):
                if command in list(Commands.BLACKJACK_ADMIN_COMMANDS.value.keys()):
                    if self._sio_data.users.get(username, 0) < 3:
                        msg = 'You don\'t have permission to do that.'
                        send_chat_msg(self._sio, msg)
                self._blackjack_processor.process_chat_command(username, command, args)
            else:
                msg = f'{command} is not a valid command'
                send_chat_msg(self._sio, msg)

        @self._sio.on('queue')
        @self._sio.on('queueWarn')
        def queue(resp):
            self._logger.info(f'queue: {resp}')
            self._sio_data.queue_err = False
            self._sio_data.queue_resp = resp

        @self._sio.on('queueFail')
        def queue_err(resp):
            acceptable_errors = [
                'This item is already on the playlist',
                'Cannot add age restricted videos. See: https://github.com/calzoneman/sync/wiki/Frequently-Asked-Questions#why-dont-age-restricted-youtube-videos-work',  # noqa: E501
                'The uploader has made this video non-embeddable',
                'This video has not been processed yet.',
            ]

            if resp['msg'] in acceptable_errors:
                self._sio_data.queue_err = False
                self._sio_data.queue_resp = resp
                return

            self._sio_data.queue_err = True
            self._logger.info(f'queue err: {resp}')
            try:
                id = resp['id']
                send_chat_msg(self._sio, f'Failed to add {id}, retrying in 4 secs.')
                self._sio.sleep(4)
                self._sio.emit(
                    'queue', {'id': id, 'type': 'yt', 'pos': 'end', 'temp': True}
                )
                # TODO: This is effectively a recursive call if cytube returns
                # errors, add a base case to kill the spawned threads and give
                # up e.g. self.err_count and max_error = 5
                while self._sio_data.queue_err:
                    self._sio.sleep(0.1)
            except KeyError:
                self._logger.info("queue err doesn't contain key 'id'")

        @self._sio.on('changeMedia')
        def change_media(resp):
            self._logger.info(f'change_media: {resp=}')
            self._sio_data.current_media = resp

        @self._sio.on('setCurrent')
        def set_current(resp):
            self._logger.info(f'set_current: {resp=}')
            self._sio_data.queue_position = resp

        @self._sio.event
        def connect_error(err):
            self._logger.info(f'Error: {err}')
            self._logger.info('Socket connection error. Attempting reconnect.')
            socket_url = self._init_socket()
            self._sio.connect(socket_url)

        @self._sio.event
        def disconnect():
            self._logger.info('Socket disconnected.')

        socket_url = self._init_socket()
        self._sio.connect(socket_url)
        self._sio.wait()
