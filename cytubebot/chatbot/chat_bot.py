import requests
import socketio
from datetime import datetime, timedelta
from cytubebot.contentfinder.database import DBHandler
from cytubebot.contentfinder.content_finder import ContentFinder
from cytubebot.randomvideo.random_finder import RandomFinder
from cytubebot.blackjack.blackjack_bot import BlackjackBot


class ChatBot:
    def __init__(self, url, channel_name, username, password) -> None:
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
            '!content', '!random', '!random_word', '!help',
            '!blackjack','!kill', '!add', '!remove'
        ]
        self.blackjack_bot = None
        self.db = DBHandler()
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
        print(f'resp: {resp.status_code} - {resp.reason}')
        servers = resp.json()
        socket_url = ''

        for server in servers['servers']:
            if server['secure']:
                socket_url = server['url']
                break

        if not socket_url:
            raise socketio.exception.ConnectionError('Unable to find a secure '
                                                     'socket to connect to')

        return socket_url

    def listen(self) -> None:
        """
        Main 'loop', connects to the socket server from _init_socket() and
        waits for chat commands.
        """
        @self.sio.event
        def connect():
            print('Socket connected!')
            self.sio.emit('joinChannel', {'name': self.channel_name})

        @self.sio.on('channelOpts')
        def channel_opts(resp):
            print(resp)
            self.sio.emit('login', {'name': self.username,
                                    'pw': self.password})

        @self.sio.on('login')
        def login(resp):
            print(resp)
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
            print(resp)
            user = resp['username']
            chat_ts = datetime.fromtimestamp(resp['time']/1000)
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
            print(f'queue: {resp}')
            self.queue_err = False
            self.queue_resp = resp

        @self.sio.on('queueFail')
        def queue_err(resp):
            acceptable_errors = [
                'This item is already on the playlist',
                'Cannot add age restricted videos. See: https://github.com/calzoneman/sync/wiki/Frequently-Asked-Questions#why-dont-age-restricted-youtube-videos-work',
                'The uploader has made this video non-embeddable',
                'This video has not been processed yet.'
            ]

            if resp['msg'] in acceptable_errors:
                self.queue_err = False
                self.queue_resp = resp
                return

            self.queue_err = True
            print(f'queue err: {resp}')
            try:
                id = resp['id']
                self.sio.emit('chatMsg', {'msg': f'Failed to add {id}, '
                                          'retrying in 2 secs.'})
                self.sio.sleep(2)
                self.sio.emit('queue', {'id': id, 'type': 'yt', 'pos': 'end',
                                        'temp': True})
                # TODO: This is effectively a recursive call if cytube returns
                # errors, add a base case to kill the spawned threads and give
                # up e.g. self.err_count and max_error = 5
                while self.queue_err:
                    self.sio.sleep(0.1)
            except KeyError:
                print('queue err doesn\'t contain key "id"')

        @self.sio.event
        def connect_error():
            print('Socket connection error. Attempting reconnect.')
            socket_url = self._init_socket()
            self.sio.connect(socket_url)

        @self.sio.event
        def disconnect():
            print('Socket disconnected.')

        socket_url = self._init_socket()
        self.sio.connect(socket_url)
        self.sio.wait()

    def process_command(self, user, command, args) -> None:
        match command:
            case '!content':
                self.lock = True
                con, cur = self.db.init_db()

                self.sio.emit('chatMsg', {'msg': 'Searching for content...'})

                self.db.pop_db()
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

                    self.sio.emit('queue', {'id': video_id, 'type': 'yt',
                                            'pos': 'end', 'temp': True})
                    while not self.queue_resp:
                        self.sio.sleep(0.3)
                    self.queue_resp = None

                    query = ('UPDATE content SET datetime = ? WHERE '
                             'channelId = ?')
                    cur.execute(query, (str(new_dt), channel_id,))
                    con.commit()

                # Close thread sensitive resources & unlock
                cur.close()
                con.close()
                self.lock = False

                self.sio.emit('chatMsg', {'msg': 'Finished adding content.'})
            case '!random' | '!random_word':
                # Not using any thread sensitive content but need to be
                # aware of self.queue_resp/queue_err etc.
                self.lock = True

                if command == '!random_word':
                    rand_id, search_str = self.random_finder.find_random(use_dict=True)
                elif command == '!random':
                    try:
                        size = int(args[0]) if args else 3
                    except ValueError:
                        size = 3

                    rand_id, search_str = self.random_finder.find_random(size)
                
                if rand_id:
                    self.sio.emit('queue', {'id': rand_id, 'type': 'yt',
                                            'pos': 'end', 'temp': True})
                    while not self.queue_resp:
                        self.sio.sleep(0.3)
                    self.queue_resp = None

                    msg = f'Searched: {search_str}, added: {rand_id}'
                    self.sio.emit('chatMsg', {'msg': msg})
                else:
                    msg = (f'Found no random videos.. Try again. '
                            'If giving arg over 5, try reducing.')
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

                try:
                    pass
                except:
                    pass
            case '!remove':
                if not args:
                    self.lock = False
                    return
            case '!help':
                msg = (f'Standard commands (admin only): {self.valid_commands}'
                       f', blackjack commands: {BlackjackBot.commands}'
                       f', blackjack admin commmands: {BlackjackBot.admin_commands}')
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
