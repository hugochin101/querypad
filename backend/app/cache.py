"""A small thread safe LRU cache for query results."""

from collections import OrderedDict
from threading import Lock
from typing import Any, Hashable


class LRUCache:
    """Least recently used cache with O(1) get and put.

    OrderedDict keeps keys in use order: a hit moves the key to the end,
    and when the cache is full the key at the front is evicted.
    """

    def __init__(self, capacity: int = 128):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._items: OrderedDict[Hashable, Any] = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            if key not in self._items:
                self.misses += 1
                return None
            self._items.move_to_end(key)
            self.hits += 1
            return self._items[key]

    def put(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            if len(self._items) > self.capacity:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size": len(self._items),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }
