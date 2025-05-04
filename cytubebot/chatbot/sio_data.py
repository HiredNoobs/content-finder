import datetime
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SIOData:
    """
    Non socket specific data class to share between classes more easily.
    """

    _queue_resp: str | None = None
    _queue_err: bool = False
    _current_backoff: int = int(os.environ.get("BASE_RETRY_BACKOFF", 2))
    _backoff_factor: int = 2
    _max_backoff: int = int(os.environ.get("MAX_RETRY_BACKOFF", 15))
    _last_retry: datetime.datetime | None = None
    _lock: bool = False
    _current_media: dict | None = None
    _queue_position: int = -1
    _users: dict = field(default_factory=dict)

    @property
    def queue_resp(self) -> str | None:
        return self._queue_resp

    @queue_resp.setter
    def queue_resp(self, value: str) -> None:
        self._queue_resp = value

    @property
    def queue_err(self) -> bool:
        return self._queue_err

    @queue_err.setter
    def queue_err(self, value: bool) -> None:
        self._queue_err = value

    @property
    def lock(self) -> bool:
        return self._lock

    @lock.setter
    def lock(self, value: bool) -> None:
        self._lock = value

    @property
    def current_media(self) -> dict | None:
        return self._current_media

    @current_media.setter
    def current_media(self, value: dict) -> None:
        self._current_media = value

    @property
    def queue_position(self) -> int:
        return self._queue_position

    @queue_position.setter
    def queue_position(self, value: int) -> None:
        self._queue_position = value

    @property
    def users(self) -> dict:
        return self._users

    @users.setter
    def users(self, value: dict) -> None:
        self._users = value

    @property
    def current_backoff(self) -> int:
        """Return the current backoff delay in seconds."""
        return self._current_backoff

    @property
    def backoff_factor(self) -> int:
        """Return the multiplier used to increase the backoff delay."""
        return self._backoff_factor

    @property
    def max_backoff(self) -> int:
        """Return the maximum allowed backoff delay in seconds."""
        return self._max_backoff

    @property
    def last_retry(self) -> datetime.datetime | None:
        """Return the timestamp of the last retry attempt."""
        return self._last_retry

    def can_retry(self) -> bool:
        """
        Check if sufficient time has passed since the last retry based on the current backoff delay.
        If no previous retry has been attempted (i.e., _last_retry is None), returns True.
        """
        if self._last_retry is None:
            return True
        elapsed = (datetime.datetime.now() - self._last_retry).total_seconds()
        return elapsed >= self._current_backoff

    def reset_backoff(self) -> None:
        """
        Reset the current backoff delay to its initial value and clear the last retry timestamp.
        """
        logger.debug("Attempting to reset backoff...")
        if self._last_retry is not None:
            # If the latest retry was recent then we won't reset
            elapsed = (datetime.datetime.now() - self._last_retry).total_seconds()
            logger.debug(f"{elapsed} seconds since {self._last_retry=}")
            if elapsed < 10:
                logger.debug(
                    f"Last retry was too soon ({elapsed} seconds ago), not resetting backoff."
                )
                return
        self._current_backoff = int(os.environ.get("BASE_RETRY_BACKOFF", 2))
        self._last_retry = None
        logger.debug(f"Backoff reset to {self._current_backoff}")

    def increase_backoff(self) -> None:
        """
        Record a retry attempt by updating the last retry timestamp and increase the current backoff delay
        exponentially, capping it at the maximum backoff value.
        """
        self._last_retry = datetime.datetime.now()
        self._current_backoff = min(
            self._current_backoff * self._backoff_factor, self._max_backoff
        )
        logger.debug(f"Current backoff increased to {self._current_backoff}")

    def add_or_update_user(self, user_id: str, user_info: dict) -> None:
        """
        Add a new user or update an existing user's information in the users dictionary.

        Parameters:
            user_id (str): A unique identifier for the user.
            user_info (dict): A dictionary of user-related information.
        """
        self._users[user_id] = user_info

    def remove_user(self, user_id: str) -> None:
        """
        Remove a user from the users dictionary by their identifier.

        Parameters:
            user_id (str): The identifier of the user to be removed.
        """
        self._users.pop(user_id, None)
