import json
import logging
import threading

import requests
from bs4 import BeautifulSoup as bs

import redis

logger = logging.getLogger(__name__)


class DatabaseWrapper:
    _instance = None
    _lock = threading.Lock()

    # Instance variable annotations for Mypy
    _host: str
    _port: int
    _redis: redis.Redis

    def __new__(cls, host: str, port: int):
        if cls._instance is None:
            with cls._lock:
                instance = super().__new__(cls)
                instance._host = host
                instance._port = port
                instance._redis = redis.Redis(
                    host=host, port=port, db=0, decode_responses=True
                )
                cls._instance = instance
        return cls._instance

    def _close_connection(self) -> None:
        logger.info("Closing Redis connection.")
        self._redis.close()

    def _make_key(self, channel_id: str) -> str:
        return f"{channel_id}@youtube.channel.id"

    def _load_channel_data(self, channel_id: str) -> dict:
        key = self._make_key(channel_id)
        data_str = self._redis.get(key)
        if data_str and isinstance(data_str, str):
            try:
                logger.debug(f"Found {key}={data_str}")
                return json.loads(data_str)
            except json.JSONDecodeError:
                logger.exception(f"Failed to decode JSON data for key: {key}")
        return {}

    def _save_channel_data(self, channel_id: str, data: dict) -> None:
        key = self._make_key(channel_id)
        logger.debug(f"Updating {key} with {data=}")
        try:
            self._redis.set(key, json.dumps(data))
        except Exception:
            logger.exception(f"Failed to save data for key: {key}")

    def update_datetime(self, channel_id: str, new_dt: str) -> None:
        data = self._load_channel_data(channel_id)
        if not data:
            logger.error(f"No channel found for ID: {channel_id}")
            return
        data["last_update"] = new_dt
        self._save_channel_data(channel_id, data)
        logger.info(f"Updated datetime for channel {channel_id}")

    def get_channels(self, tag: str | None = None) -> list:
        channels = []
        pattern = "*@youtube.channel.id"
        # scan_iter instead of keys to be more production friendly
        for key in self._redis.scan_iter(pattern):
            data_str = self._redis.get(key)
            if data_str and isinstance(data_str, str):
                try:
                    data = json.loads(data_str)
                    if tag:
                        if (
                            "tags" in data
                            and isinstance(data["tags"], list)
                            and tag in data["tags"]
                        ):
                            channels.append(data)
                    else:
                        channels.append(data)
                except json.JSONDecodeError:
                    logger.exception(f"JSON decoding failed for key: {key}")
        return channels

    def add_channel(self, channel_id: str, channel_name: str) -> None:
        channel_url = (
            f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        )
        try:
            resp = requests.get(channel_url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            logger.exception(f"Failed to retrieve feed for channel_id: {channel_id}")
            return

        soup = bs(resp.text, "lxml")
        try:
            entry = soup.find_all("entry")[0]
            published = entry.find_all("published")[0].text
        except (IndexError, AttributeError):
            logger.error(f"Failed to parse published date for channel_id: {channel_id}")
            return

        data = {
            "channelId": channel_id,
            "name": channel_name,
            "last_update": published,
            "tags": [],
        }
        self._save_channel_data(channel_id, data)
        logger.info(f"Added channel {channel_id} with name {channel_name}")

    def remove_channel(self, channel_name: str) -> None:
        pattern = "*@youtube.channel.id"
        for key in self._redis.scan_iter(pattern):
            data_str = self._redis.get(key)
            if data_str and isinstance(data_str, str):
                try:
                    data = json.loads(data_str)
                    if data.get("name") == channel_name:
                        self._redis.delete(key)
                        logger.info(f"Removed channel with name {channel_name}")
                        return
                except json.JSONDecodeError:
                    logger.exception(f"JSON decoding failed for key: {key}")
        logger.warning(f"No channel found with name {channel_name}")

    def add_tags(self, channel_id: str, new_tags: list) -> None:
        data = self._load_channel_data(channel_id)
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        for tag in new_tags:
            if tag not in tags:
                tags.append(tag)
        data["tags"] = tags
        self._save_channel_data(channel_id, data)
        logger.info(f"Added tags {new_tags} to channel {channel_id}")

    def remove_tags(self, channel_id: str, tags_to_remove: list) -> None:
        data = self._load_channel_data(channel_id)
        if not data:
            logger.error(f"No channel found for ID: {channel_id}")
            return
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        data["tags"] = [tag for tag in tags if tag not in tags_to_remove]
        self._save_channel_data(channel_id, data)
        logger.info(f"Removed tags {tags_to_remove} from channel {channel_id}")

    def shutdown(self) -> None:
        logger.debug("Shutting down DB remotely...")
        self._redis.shutdown()

    @property
    def connection(self) -> redis.Redis:
        return self._redis
