import logging

import requests
import socketio

from cytubebot.chatbot.chat_processor import ChatProcessor
from cytubebot.chatbot.sio_data import SIOData


class ChatBot:
    """
    The ChatBot class is a socketio wrapper that handles **only** the socket
    side of the chat bot. Processing chat should be passed to ChatProcessor.
    """

    def __init__(
        self, url: str, channel_name: str, username: str, password: str
    ) -> None:
        self._logger = logging.getLogger(__name__)

        self.url = url
        self.channel_name = channel_name
        self.username = username
        self.password = password

        self.sio = socketio.Client()  # For debugging: engineio_logger=True
        self._sio_data = SIOData()
        self._chat_processor = ChatProcessor(self.sio, self._sio_data)

    def _init_socket(self) -> str:
        """
        Finds the socket conn for channel given in .env - this method does NOT
        connect.

        returns:
            A str containing the url of the socket server.
        """
        socket_conf = f'{self.url}socketconfig/{self.channel_name}.json'
        resp = requests.get(socket_conf)
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

        @self.sio.event
        def connect():
            self._logger.info('Socket connected!')
            self.sio.emit('joinChannel', {'name': self.channel_name})

        @self.sio.on('channelOpts')
        def channel_opts(resp):
            self._logger.info(resp)
            self.sio.emit('login', {'name': self.username, 'pw': self.password})

        @self.sio.on('login')
        def login(resp):
            self._logger.info(resp)
            self.sio.emit('chatMsg', {'msg': 'Hello!'})

        @self.sio.on('userlist')
        def userlist(resp):
            for user in resp:
                self._sio_data.users[user['name']] = user['rank']

        @self.sio.on('addUser')
        @self.sio.on('setUserRank')
        def user_add(resp):
            self._sio_data.users[resp['name']] = resp['rank']

        @self.sio.on('userLeave')
        def user_leave(resp):
            self._sio_data.users.pop(resp['name'], None)

        @self.sio.on('chatMsg')
        def chat(resp):
            self._logger.info(resp)
            self._chat_processor.process_chat(resp)

        @self.sio.on('queue')
        @self.sio.on('queueWarn')
        def queue(resp):
            self._logger.info(f'queue: {resp}')
            self._sio_data.queue_err = False
            self._sio_data.queue_resp = resp

        @self.sio.on('queueFail')
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
                self.sio.emit(
                    'chatMsg', {'msg': f'Failed to add {id}, ' 'retrying in 2 secs.'}
                )
                self.sio.sleep(2)
                self.sio.emit(
                    'queue', {'id': id, 'type': 'yt', 'pos': 'end', 'temp': True}
                )
                # TODO: This is effectively a recursive call if cytube returns
                # errors, add a base case to kill the spawned threads and give
                # up e.g. self.err_count and max_error = 5
                while self._sio_data.queue_err:
                    self.sio.sleep(0.1)
            except KeyError:
                self._logger.info("queue err doesn't contain key 'id'")

        @self.sio.event
        def connect_error():
            self._logger.info('Socket connection error. Attempting reconnect.')
            socket_url = self._init_socket()
            self.sio.connect(socket_url)

        @self.sio.event
        def disconnect():
            self._logger.info('Socket disconnected.')

        socket_url = self._init_socket()
        self.sio.connect(socket_url)
        self.sio.wait()
