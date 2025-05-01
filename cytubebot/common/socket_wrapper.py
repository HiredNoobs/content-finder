import logging
import os
import threading
from textwrap import wrap

import requests
import socketio

from cytubebot.chatbot.sio_data import SIOData

MSG_LIMIT = int(os.environ.get("CYTUBE_MSG_LIMIT", "80"))


class SocketWrapper:
    _instance = None
    _lock = threading.Lock()

    # Instance variable annotations for Mypy
    _url: str
    _channel_name: str
    _logger: logging.Logger
    _socketio: socketio.Client
    data: SIOData

    def __new__(cls, url: str, channel_name: str):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)

                instance._url = url
                instance._channel_name = channel_name
                instance._logger = logging.getLogger(__name__)

                # For debugging: engineio_logger=True
                instance._socketio = socketio.Client()
                instance.data = SIOData()
                cls._instance = instance

                # socket_url = instance.init_socket()
                # instance._socketio.connect(socket_url)
        return cls._instance

    def init_socket(self) -> str:
        """
        Returns:
            A str containing the URL of the socket server.
        """
        socket_conf = f"{self._url}/socketconfig/{self._channel_name}.json"
        resp = requests.get(socket_conf, timeout=60)
        self._logger.info(f"resp: {resp.status_code} - {resp.reason}")
        servers = resp.json()
        socket_url = ""

        for server in servers["servers"]:
            if server["secure"]:
                socket_url = server["url"]
                break

        if not socket_url:
            raise socketio.exceptions.ConnectionError(
                "Unable to find a secure socket to connect to"
            )

        return socket_url

    def send_chat_msg(self, message: str) -> None:
        """
        Sends a chat message through the socket.
        The message is split into chunks of size MSG_LIMIT using textwrap.wrap,
        and each chunk is emitted as a "chatMsg" event.
        """
        msgs = wrap(message, MSG_LIMIT)
        for msg in msgs:
            self._socketio.emit("chatMsg", {"msg": msg})

    def __getattr__(self, name):
        """
        Forward attribute access to the underlying SocketIO instance.
        This allows you to call any of SocketIO's methods on the singleton.
        """
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr(self._socketio, name)
