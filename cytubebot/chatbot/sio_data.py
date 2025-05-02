from dataclasses import dataclass, field


@dataclass
class SIOData:
    """
    Non socket specific data class to share between classes more easily.
    """

    _queue_resp: str | None = None  # Stores the most recent response when content added to queue
    _queue_err: bool = False  # Stores a bool to reflect if the _queue_resp was an error
    _lock: bool = False
    _current_media: dict = None
    _queue_position: int = -1
    _users: dict = field(default_factory=dict)

    @property
    def queue_resp(self) -> str:
        return self._queue_resp

    @queue_resp.setter
    def queue_resp(self, value: str) -> None:
        self._queue_resp = value

    @property
    def queue_err(self) -> bool:
        return self._queue_err

    @queue_err.setter
    def queue_err(self, value: str) -> None:
        self._queue_err = value

    @property
    def lock(self) -> bool:
        return self._lock

    @lock.setter
    def lock(self, value: str) -> None:
        self._lock = value

    @property
    def current_media(self) -> dict:
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
    def users(self, value: str) -> None:
        self._users = value
