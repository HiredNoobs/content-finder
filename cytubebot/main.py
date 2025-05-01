import os

from cytubebot.chatbot.chat_bot import ChatBot
from cytubebot.common.exceptions import MissingEnvVar
from cytubebot.common.socket_wrapper import SocketWrapper


def main() -> None:
    url = os.getenv("CYTUBE_URL")
    channel_name = os.getenv("CYTUBE_URL_CHANNEL_NAME")
    username = os.getenv("CYTUBE_USERNAME")
    password = os.getenv("CYTUBE_PASSWORD")

    if not url or not channel_name or not username or not password:
        raise MissingEnvVar("One/some of the env variables are missing.")

    # Create the singleton
    SocketWrapper(url, channel_name)

    bot = ChatBot(username, password)
    bot.listen()


if __name__ == "__main__":
    main()
