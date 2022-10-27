from dataclasses import dataclass, field


@dataclass
class SIOData:
    """
    Non socket specific data class to share between classes more easily.
    """

    _queue_resp: str = None
    _queue_err: bool = False
    _lock: bool = False
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
    def users(self) -> dict:
        return self._users

    @users.setter
    def users(self, value: str) -> None:
        self._users = value
