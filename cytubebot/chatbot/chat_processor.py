import logging
import re

import requests
from bs4 import BeautifulSoup as bs

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

        self._db = DBHandler()
        self._random_finder = RandomFinder()
        self._content_finder = ContentFinder()

    def process_chat_command(self, command, args, allow_force=False) -> None:
        if self._sio_data.lock and not (allow_force and args and args[0] == "--force"):
            send_chat_msg(self._sio, "Already busy, please wait...")
            return

        self._sio_data.lock = True
        try:
            self._process_command(command, args)
        except Exception as err:
            self._logger.exception(f"Error while processing command {command}: {err}")
            send_chat_msg(self._sio, f"Error processing command: {err}")
        finally:
            self._sio_data.lock = False

    def _process_command(self, command, args) -> None:
        match command:
            case "content":
                tag = args[0].upper() if args else None
                content_handler(
                    self._content_finder, tag, self._db, self._sio, self._sio_data
                )
            case "random" | "random_word":
                random_handler(
                    command, args, self._random_finder, self._sio, self._sio_data
                )
            case "current":
                self._handle_current()
            case "add":
                add_user(args, self._db, self._sio)
            case "remove":
                remove_user(args, self._db, self._sio)
            case "add_tags" | "remove_tags":
                self._handle_tags(command, args)
            case "christmas" | "xmas":
                add_christmas_videos(self._sio)
            case "help":
                self._handle_help()
            case "kill":
                self._handle_kill()
            case _:
                send_chat_msg(self._sio, f"Unknown command: {command}")

    def _handle_current(self) -> None:
        try:
            self._sio.emit("playerReady")
            curr = self._sio_data.current_media
            video_id = curr.get("id")
            if not video_id:
                raise ValueError("No video id found in current media")
            url = f"https://www.youtube.com/watch?v={video_id}"
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            soup = bs(resp.text, "lxml")
            script = soup.find("script", string=re.compile("ytInitialPlayerResponse"))
            if not script:
                raise ValueError("ytInitialPlayerResponse not found in page source.")

            match_obj = re.search('.*"description":{"simpleText":"(.*?)"', script.text)
            if match_obj:
                description = match_obj.group(1).replace("\\n", " ")
                curr["description"] = description
            else:
                curr["description"] = "Description not available"

            self._logger.info("Current media: %s", curr)
            send_chat_msg(self._sio, f"{curr}")
        except Exception as err:
            self._logger.exception(f"Error handling 'current' command: {err}")
            send_chat_msg(self._sio, f"Error retrieving current media: {err}")

    def _handle_tags(self, command: str, args: list) -> None:
        try:
            if command == "add_tags":
                add_tags(args, self._db)
            else:
                remove_tags(args, self._db)
        except IndexError:
            send_chat_msg(self._sio, "Not enough args supplied for !add_tags.")
        except InvalidTagError:
            send_chat_msg(self._sio, f"One or more tags in {args[1:]} is invalid.")

    def _handle_help(self) -> None:
        """
        Provides help information by listing available commands.
        """
        msg = (
            f"Use any of {Commands.COMMAND_SYMBOLS.value} with: "
            f"{Commands.STANDARD_COMMANDS.value}, "
            f"{Commands.ADMIN_COMMANDS.value}, "
            f"{Commands.BLACKJACK_COMMANDS.value}, "
            f"{Commands.BLACKJACK_ADMIN_COMMANDS.value}"
        )
        send_chat_msg(self._sio, msg)

    def _handle_kill(self) -> None:
        try:
            response = requests.get(
                "http://postgres.content-finder:5000/shutdown", timeout=60
            )
            response.raise_for_status()
            send_chat_msg(self._sio, "Bye bye!")
            self._sio.sleep(3)  # Allows time for the chat message to be sent
        except Exception as err:
            self._logger.exception(f"Error during kill command: {err}")
        finally:
            self._sio.disconnect()
