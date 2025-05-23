import logging
import os
from datetime import datetime, timedelta

from cytubebot.blackjack.blackjack_bot import BlackjackBot
from cytubebot.chatbot.chat_processor import ChatProcessor
from cytubebot.common.commands import Commands
from cytubebot.common.socket_wrapper import SocketWrapper

REQUIRED_PERMISSION_LEVEL = 3
ACCEPTABLE_ERRORS = [
    "This item is already on the playlist",
    "Cannot add age restricted videos. See: https://github.com/calzoneman/sync/wiki/Frequently-Asked-Questions#why-dont-age-restricted-youtube-videos-work",
    "The uploader has made this video non-embeddable",
    "This video has not been processed yet.",
]
logger = logging.getLogger(__name__)


class ChatBot:
    """
    The ChatBot class is a socketio wrapper that handles **only** the socket
    side of the chat bot and basic processing, any specific processing
    should be passed to the relevant class.
    """

    def __init__(self, channel_name: str, username: str, password: str) -> None:
        self._channel_name = channel_name
        self._username = username
        self._password = password

        self._sio = SocketWrapper("", "")
        self._chat_processor = ChatProcessor()
        self._blackjack_bot = BlackjackBot()

    def listen(self) -> None:
        """
        Main 'loop', connects to the socket server from _init_socket() and
        waits for chat commands.
        """

        def has_permission(
            username: str, required: int = REQUIRED_PERMISSION_LEVEL
        ) -> bool:
            return self._sio.data.users.get(username, 0) >= required

        standard_commands = set(Commands.STANDARD_COMMANDS.value.keys())
        admin_commands = set(Commands.ADMIN_COMMANDS.value.keys())
        blackjack_commands = set(Commands.BLACKJACK_COMMANDS.value.keys())
        blackjack_admin_commands = set(Commands.BLACKJACK_ADMIN_COMMANDS.value.keys())
        command_symbols = tuple(Commands.COMMAND_SYMBOLS.value)

        @self._sio.event
        def connect():
            logger.info("Socket connected!")
            self._sio.emit("joinChannel", {"name": self._channel_name})

        @self._sio.on("channelOpts")
        def channel_opts(resp):
            logger.info(resp)
            self._sio.emit("login", {"name": self._username, "pw": self._password})

        @self._sio.on("login")
        def login(resp):
            logger.info(resp)
            self._sio.send_chat_msg("Hello!")

        @self._sio.on("userlist")
        def userlist(resp):
            for user in resp:
                self._sio.data.add_or_update_user(user["name"], user["rank"])

        @self._sio.on("addUser")  # User joins channel
        @self._sio.on("setUserRank")
        def user_add(resp):
            self._sio.data.add_or_update_user(resp["name"], resp["rank"])

        @self._sio.on("userLeave")
        def user_leave(resp):
            self._sio.data.remove_user(resp["name"])
            self._blackjack_bot.blackjack.remove_player(resp["name"])

        @self._sio.on("chatMsg")
        def chat(resp):
            logger.debug(resp)

            username = resp["username"]
            raw_message = resp["msg"]
            chat_ts = datetime.fromtimestamp(resp["time"] / 1000)

            # Only process messages sent within the last 10 seconds from a user other than self.
            if chat_ts < datetime.now() - timedelta(
                seconds=10
            ) or username == os.getenv("CYTUBE_USERNAME"):
                logger.debug(
                    f"Not processing {resp} due to either age or message from bot."
                )
                return

            parts = raw_message.split()
            if not parts:
                return

            raw_command = parts[0].casefold()
            # Verify that the message starts with a valid command symbol.
            if not raw_command.startswith(command_symbols):
                return

            logger.debug(f"Processing {raw_command}")

            command = raw_command[1:]
            args = parts[1:] if len(parts) > 1 else []

            # Process normal / admin chat commands.
            if command in standard_commands or command in admin_commands:
                if command in admin_commands:
                    if not has_permission(username):
                        self._sio.send_chat_msg("You don't have permission to do that.")
                        return
                    self._chat_processor.process_chat_command(
                        command, args, allow_force=True
                    )
                else:
                    self._chat_processor.process_chat_command(command, args)
            # Process blackjack commands.
            elif command in blackjack_commands or command in blackjack_admin_commands:
                if command in blackjack_admin_commands and not has_permission(username):
                    self._sio.send_chat_msg("You don't have permission to do that.")
                    return
                self._blackjack_bot.process_chat_command(username, command, args)
            else:
                self._sio.send_chat_msg(f"{command} is not a valid command")

        @self._sio.on("queue")
        @self._sio.on("queueWarn")
        def queue(resp):
            logger.info(f"queue: {resp}")
            self._sio.data.queue_err = False
            self._sio.data.queue_resp = resp
            self._sio.data.reset_backoff()

        @self._sio.on("queueFail")
        def queue_err(resp):
            logger.debug(f"queue err: {resp}")

            if resp["msg"] in ACCEPTABLE_ERRORS:
                logger.debug(
                    f"Skipping '{resp['msg']}' due to being an acceptable error for {resp['id']}."
                )
                self._sio.data.queue_err = False
                self._sio.data.queue_resp = resp
                self._sio.data.reset_backoff()
                return

            self._sio.data.queue_err = True
            delay = self._sio.data.current_backoff

            try:
                video_id = resp["id"]

                if not self._sio.data.can_retry():
                    self._sio.send_chat_msg(
                        f"Failed to add {video_id}, retrying in {delay} seconds."
                    )
                    self._sio.data.last_retry = datetime.now()
                    self._sio.sleep(delay)
                    self._sio.data.increase_backoff()
                else:
                    self._sio.data.last_retry = datetime.now()

                self._sio.add_video_to_queue(video_id, wait=False)
            except KeyError:
                logger.info("queue err response doesn't contain key 'id'")

        @self._sio.on("changeMedia")
        def change_media(resp):
            logger.info(f"change_media: {resp=}")
            self._sio.data.current_media = resp

        @self._sio.on("setCurrent")
        def set_current(resp):
            logger.info(f"set_current: {resp=}")
            self._sio.data.queue_position = resp

        @self._sio.event
        def connect_error(err):
            logger.info(f"Error: {err}")
            logger.info("Socket connection error. Attempting reconnect.")
            # Is this fine? Or are we doing something recursive?
            socket_url = self._sio.init_socket()
            self._sio.connect(socket_url)

        @self._sio.event
        def disconnect():
            logger.info("Socket disconnected.")

        socket_url = self._sio.init_socket()
        self._sio.connect(socket_url)
        self._sio.wait()
