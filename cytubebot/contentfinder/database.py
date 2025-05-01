import atexit
import json
import logging
import os

import requests
from bs4 import BeautifulSoup as bs

import redis


# TODO:
# - Move logger out of class
# - Convert to singleton with static methods
class DBHandler:
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        self._redis = redis.Redis(host=host, port=port, db=0, decode_responses=True)
        atexit.register(self._close_connection)

    def _close_connection(self) -> None:
        self._logger.info("Closing Redis connection.")
        self._redis.close()

    def _make_key(self, channel_id: str) -> str:
        return f"{channel_id}@youtube.channel.id"

    def _load_channel_data(self, channel_id: str) -> dict:
        key = self._make_key(channel_id)
        data_str = self._redis.get(key)
        if data_str:
            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                self._logger.exception(f"Failed to decode JSON data for key: {key}")
        return {}

    def _save_channel_data(self, channel_id: str, data: dict) -> None:
        key = self._make_key(channel_id)
        try:
            self._redis.set(key, json.dumps(data))
        except Exception:
            self._logger.exception(f"Failed to save data for key: {key}")

    def update_datetime(self, channel_id: str, new_dt: str) -> None:
        data = self._load_channel_data(channel_id)
        if not data:
            self._logger.error(f"No channel found for ID: {channel_id}")
            return
        data["datetime"] = new_dt
        self._save_channel_data(channel_id, data)
        self._logger.info(f"Updated datetime for channel {channel_id}")

    def get_channels(self, tag: str | None = None) -> list:
        channels = []
        pattern = "*@youtube.channel.id"
        # scan_iter instead of keys to be more production friendly
        for key in self._redis.scan_iter(pattern):
            data_str = self._redis.get(key)
            if data_str:
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
                    self._logger.exception(f"JSON decoding failed for key: {key}")
        return channels

    def add_channel(self, channel_id: str, channel_name: str) -> None:
        channel_url = (
            f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        )
        try:
            resp = requests.get(channel_url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            self._logger.exception(
                f"Failed to retrieve feed for channel_id: {channel_id}"
            )
            return

        soup = bs(resp.text, "lxml")
        try:
            entry = soup.find_all("entry")[0]
            published = entry.find_all("published")[0].text
        except (IndexError, AttributeError):
            self._logger.error(
                f"Failed to parse published date for channel_id: {channel_id}"
            )
            return

        data = {
            "channelId": channel_id,
            "name": channel_name,
            "datetime": published,
            "tags": [],
        }
        self._save_channel_data(channel_id, data)
        self._logger.info(f"Added channel {channel_id} with name {channel_name}")

    def remove_channel(self, channel_name: str) -> None:
        pattern = "*@youtube.channel.id"
        for key in self._redis.scan_iter(pattern):
            data_str = self._redis.get(key)
            if data_str:
                try:
                    data = json.loads(data_str)
                    if data.get("name") == channel_name:
                        self._redis.delete(key)
                        self._logger.info(f"Removed channel with name {channel_name}")
                        return
                except json.JSONDecodeError:
                    self._logger.exception(f"JSON decoding failed for key: {key}")
        self._logger.warning(f"No channel found with name {channel_name}")

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
        self._logger.info(f"Added tags {new_tags} to channel {channel_id}")

    def remove_tags(self, channel_id: str, tags_to_remove: list) -> None:
        data = self._load_channel_data(channel_id)
        if not data:
            self._logger.error(f"No channel found for ID: {channel_id}")
            return
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        data["tags"] = [tag for tag in tags if tag not in tags_to_remove]
        self._save_channel_data(channel_id, data)
        self._logger.info(f"Removed tags {tags_to_remove} from channel {channel_id}")

    @property
    def connection(self) -> redis.Redis:
        return self._redis
