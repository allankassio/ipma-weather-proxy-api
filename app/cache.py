import time
from typing import Any, Dict, Optional, Tuple

class TTLCache:
    """Simple TTL-backed key-value cache.

    Parameters
    ----------
    ttl_seconds : int
        Time-to-live in seconds. Items older than this are considered expired.

    Notes
    -----
    - Keys are typed as `str` in this implementation.
    - Operations are O(1) average time.
    - Expiration is lazy (on `get`); there is no background reaper.
    """

    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for `key` if present and not expired.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Optional[Any]
            The stored value, or `None` if the key is missing or the entry expired.

        Notes
        -----
        - Performs lazy eviction: if the entry is stale, it is removed and `None` is returned.
        """

        now = time.time()
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if now - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Insert or replace a value for `key`, timestamped for TTL accounting.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Arbitrary Python object to store.
        """

        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        """Remove all entries from the cache.

        Useful for tests or to force a full refresh of cached data.
        """

        self._store.clear()
