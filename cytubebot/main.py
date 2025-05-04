import os

from cytubebot.chatbot.chat_bot import ChatBot
from cytubebot.common.database_wrapper import DatabaseWrapper
from cytubebot.common.exceptions import MissingEnvVar
from cytubebot.common.socket_wrapper import SocketWrapper


def main() -> None:
    url = os.getenv("CYTUBE_URL")
    channel_name = os.getenv("CYTUBE_URL_CHANNEL_NAME")
    username = os.getenv("CYTUBE_USERNAME")
    password = os.getenv("CYTUBE_PASSWORD")

    db_host = os.getenv("REDIS_HOST", "localhost")
    db_port = int(os.getenv("REDIS_PORT", 6379))

    if not url or not channel_name or not username or not password:
        raise MissingEnvVar("One/some of the env variables are missing.")

    # Create the singletons
    SocketWrapper(url, channel_name)
    DatabaseWrapper(db_host, db_port)

    bot = ChatBot(channel_name, username, password)
    bot.listen()


if __name__ == "__main__":
    main()
