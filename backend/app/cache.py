"""SQLite cache for external API responses.

Every Last.fm / MusicBrainz request goes through fetch_json() below, which
checks the cache first and only touches the network on a miss. That keeps us
fast, polite to the APIs, and lets the engine be re-run without re-downloading.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from app.ratelimit import RateLimiter

# Params left out of the cache key. The API key doesn't change the answer, and
# leaving it out means it never gets written into cache.db.
IGNORED_PARAMS = {"api_key"}

# Tags and similar artists change slowly, so a month-old answer is fine.
DEFAULT_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def make_key(endpoint: str, params: dict) -> str:
    """Normalize a request into a cache key: endpoint + params sorted by name.

    Sorting means {"a": 1, "b": 2} and {"b": 2, "a": 1} hit the same entry.
    """
    kept = {name: str(value).strip() for name, value in params.items() if name not in IGNORED_PARAMS}
    return endpoint + "?" + json.dumps(kept, sort_keys=True)


class Cache:
    def __init__(self, path: Path | str):
        # FastAPI handles requests on several threads. SQLite connections refuse
        # cross-thread use by default, so we allow it and use a lock to make
        # sure only one thread touches the connection at a time.
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            " key TEXT PRIMARY KEY,"
            " body TEXT NOT NULL,"  # the parsed JSON response, re-serialized
            " fetched_at REAL NOT NULL"  # unix timestamp, used for expiry
            ")"
        )
        self.conn.commit()

    def get(self, key: str, max_age: float = DEFAULT_MAX_AGE_SECONDS) -> Any | None:
        with self.lock:
            row = self.conn.execute("SELECT body, fetched_at FROM responses WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        body, fetched_at = row
        if time.time() - fetched_at > max_age:
            return None  # stale; the caller will refetch and overwrite it
        return json.loads(body)

    def set(self, key: str, data: Any) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO responses (key, body, fetched_at) VALUES (?, ?, ?)",
                (key, json.dumps(data), time.time()),
            )
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()


def fetch_json(
    cache: Cache,
    http: httpx.Client,
    url: str,
    params: dict,
    *,
    limiter: RateLimiter,
    parse: Callable[[httpx.Response], Any],
) -> Any:
    """GET url with params, going through the cache.

    `parse` turns the raw response into data, or raises if the response is an
    error. Because it raises before cache.set() runs, errors are never cached.
    """
    key = make_key(url, params)
    cached = cache.get(key)
    if cached is not None:
        return cached  # cache hits don't count against the rate limit

    limiter.wait()
    response = http.get(url, params=params)
    data = parse(response)
    cache.set(key, data)
    return data
