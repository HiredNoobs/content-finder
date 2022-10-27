import logging
import re
from datetime import datetime, timedelta

import psycopg
import requests
import socketio
from bs4 import BeautifulSoup as bs

from cytubebot.blackjack.blackjack_bot import BlackjackBot
from cytubebot.contentfinder.content_finder import ContentFinder
from cytubebot.contentfinder.database import DBHandler
from cytubebot.randomvideo.random_finder import RandomFinder


class ChatBot:
    def __init__(self, url, channel_name, username, password) -> None:
        self._logger = logging.getLogger(__name__)

        self.url = url
        self.channel_name = channel_name
        self.username = username
        self.password = password

        self.sio = socketio.Client()  # For debugging: engineio_logger=True
        self.queue_resp = None

        # To avoid issues with different threads (i.e. main and error thread)
        # changing queue_resp while another thread is waiting for it to have a
        # specific value
        self.queue_err = False
        self.lock = False
        self.users = {}
        self.valid_commands = [
            '!content',
            '!random',
            '!random_word',
            '!help',
            '!blackjack',
            '!kill',
            '!add',
            '!remove',
        ]
        self.blackjack_bot = None
        self._db = DBHandler()
        self.content_finder = ContentFinder()

        self.random_finder = RandomFinder()

    def _init_socket(self) -> str:
        """
        Finds the socket conn for channel given in .env -  this method does NOT
        connect.

        returns:
            A str containing the url of the socket server.
        """
        socketConfig = f'{self.url}socketconfig/{self.channel_name}.json'
        resp = requests.get(socketConfig)
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
                self.users[user['name']] = user['rank']

        @self.sio.on('addUser')
        @self.sio.on('setUserRank')
        def user_add(resp):
            self.users[resp['name']] = resp['rank']

        @self.sio.on('userLeave')
        def user_leave(resp):
            self.users.pop(resp['name'], None)

        @self.sio.on('chatMsg')
        def chat(resp):
            self._logger.info(resp)
            user = resp['username']
            chat_ts = datetime.fromtimestamp(resp['time'] / 1000)
            delta = datetime.now() - timedelta(seconds=10)

            # Temp fix due to cytube being 30 seconds behind reality
            delta = delta - timedelta(seconds=90)

            command = resp['msg'].split()[0].casefold()

            try:
                args = [x.casefold() for x in resp['msg'].split()[1:]]
            except IndexError:
                args = None

            # Ignore older messages and messages that aren't valid commands
            if chat_ts < delta:
                return

            if command not in self.valid_commands:
                # If it's not a reg command, check blackjack
                # All players will have access to blackjack, move under
                # if self.users.get(resp['username'], 0) < 3 to only allow admins
                if self.blackjack_bot:
                    if command in self.blackjack_bot.commands:
                        self.blackjack_bot.process_command(user, command, args)
                        return
                    # We'll deal with these later after perms have been checked
                    elif command in self.blackjack_bot.admin_commands:
                        pass
                    else:
                        return
                else:
                    return

            if self.users.get(resp['username'], 0) < 3:
                msg = 'You don\'t have permission to do that.'
                self.sio.emit('chatMsg', {'msg': msg})
                return

            # Check for blackjack admin only commands
            if self.blackjack_bot:
                if command in self.blackjack_bot.admin_commands:
                    self.blackjack_bot.process_command(user, command, args)
                    return

            if self.lock:
                msg = 'Currently collecting content, please wait...'
                self.sio.emit('chatMsg', {'msg': msg})
                return

            self.process_command(user, command, args)

        @self.sio.on('queue')
        @self.sio.on('queueWarn')
        def queue(resp):
            self._logger.info(f'queue: {resp}')
            self.queue_err = False
            self.queue_resp = resp

        @self.sio.on('queueFail')
        def queue_err(resp):
            acceptable_errors = [
                'This item is already on the playlist',
                'Cannot add age restricted videos. See: https://github.com/calzoneman/sync/wiki/Frequently-Asked-Questions#why-dont-age-restricted-youtube-videos-work',  # noqa: E501
                'The uploader has made this video non-embeddable',
                'This video has not been processed yet.',
            ]

            if resp['msg'] in acceptable_errors:
                self.queue_err = False
                self.queue_resp = resp
                return

            self.queue_err = True
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
                while self.queue_err:
                    self.sio.sleep(0.1)
            except KeyError:
                self._logger.info('queue err doesn\'t contain key "id"')

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

    def process_command(self, user, command, args) -> None:
        self.lock = True
        match command:
            case '!content':
                self.sio.emit('chatMsg', {'msg': 'Searching for content...'})

                content, count = self.content_finder.find_content()

                if count == 0:
                    self.sio.emit('chatMsg', {'msg': 'No content to add.'})
                    self.lock = False
                    return

                self.sio.emit('chatMsg', {'msg': f'Adding {count} videos.'})

                for content_tuple in content:
                    channel_id = content_tuple.channel_id
                    new_dt = content_tuple.datetime
                    video_id = content_tuple.video_id

                    self.sio.emit(
                        'queue',
                        {'id': video_id, 'type': 'yt', 'pos': 'end', 'temp': True},
                    )
                    while not self.queue_resp:
                        self.sio.sleep(0.3)
                    self.queue_resp = None

                    self._db.update_datetime(channel_id, str(new_dt))

                self.lock = False

                self.sio.emit('chatMsg', {'msg': 'Finished adding content.'})
            case '!random' | '!random_word':
                if command == '!random_word':
                    rand_id, search_str = self.random_finder.find_random(use_dict=True)
                elif command == '!random':
                    try:
                        size = int(args[0]) if args else 3
                    except ValueError:
                        size = 3

                    rand_id, search_str = self.random_finder.find_random(size)

                if rand_id:
                    self.sio.emit(
                        'queue',
                        {'id': rand_id, 'type': 'yt', 'pos': 'end', 'temp': True},
                    )
                    while not self.queue_resp:
                        self.sio.sleep(0.3)
                    self.queue_resp = None

                    msg = f'Searched: {search_str}, added: {rand_id}'
                    self.sio.emit('chatMsg', {'msg': msg})
                else:
                    msg = (
                        'Found no random videos.. Try again. '
                        'If giving arg over 5, try reducing.'
                    )
                    self.sio.emit('chatMsg', {'msg': msg})

                self.lock = False
            case '!blackjack':
                if self.blackjack_bot:
                    msg = 'Blackjack game already in progress, try !join'
                    self.sio.emit('chatMsg', {'msg': msg})
                    return
                if args:
                    self.blackjack_bot = BlackjackBot(self.sio, user, args[0])
                else:
                    self.blackjack_bot = BlackjackBot(self.sio, user)
                msg = 'Starting blackjack, use !join to play.'
                self.sio.emit('chatMsg', {'msg': msg})
            case '!add':
                if not args:
                    self.lock = False
                    return

                channel_name = ''.join(args)
                channel_name = channel_name.strip().lower()

                # Remove <a> tags if necessary
                if '</a>' in channel_name:
                    channel_name = re.search(r'.*>(.*?)</a>', channel_name).group(1)

                if 'https://www.youtube.com/c/' not in channel_name:
                    channel = f'https://www.youtube.com/c/{channel_name}'
                else:
                    channel = channel_name

                resp = requests.get(channel, cookies={'CONSENT': 'YES+1'})
                soup = bs(resp.text, 'lxml')
                yt_initial_data = soup.find(
                    'script', string=re.compile('ytInitialData')
                )
                try:
                    results = re.search(
                        '.*"browse_id","value":"(.*?)"', yt_initial_data.text
                    )
                except AttributeError:
                    msg = f"Couldn't find channel ID for {channel}"
                    self._logger.error(msg)
                    self.sio.emit('chatMsg', {'msg': msg})
                    self.lock = False
                    return

                channel_id = results.group(1)
                msg = (
                    f'Found channel ID: {channel_id} for {channel_name}, adding to DB.'
                )
                self.sio.emit('chatMsg', {'msg': msg})

                try:
                    self._db.add_channel(channel_id, channel_name)
                except psycopg.errors.UniqueViolation:
                    msg = f'{channel_name} already in Database.'
                    self.sio.emit('chatMsg', {'msg': msg})

                self.lock = False
            case '!remove':
                if not args:
                    self.lock = False
                    return

                channel_name = ''.join(args)
                channel_name = channel_name.strip().lower()

                # Remove <a> tags if necessary
                if '</a>' in channel_name:
                    channel_name = re.search(r'.*>(.*?)</a>', channel_name).group(1)

                msg = f'Deleting {channel_name} from DB.'
                self.sio.emit('chatMsg', {'msg': msg})

                self._db.remove_channel(channel_name)
            case '!help':
                msg = (
                    f'Standard commands (admin only): {self.valid_commands}'
                    f', blackjack commands: {BlackjackBot.commands}'
                    f', blackjack admin commmands: {BlackjackBot.admin_commands}'
                )
                self.sio.emit('chatMsg', {'msg': msg})
            case '!kill':
                self.lock = True
                if self.blackjack_bot:
                    self.blackjack_bot.kill = True
                self.sio.emit('chatMsg', {'msg': 'Bye bye!'})
                self.sio.sleep(3)  # temp sol to allow the chat msg to send
                self.sio.disconnect()
            case _:
                msg = f'Missing case for command {command}'
                self.sio.emit('chatMsg', {'msg': msg})

        self.lock = False
