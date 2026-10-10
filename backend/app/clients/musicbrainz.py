"""MusicBrainz API client: release-group search and lookup by ID.

Docs: https://musicbrainz.org/doc/MusicBrainz_API
Rules: send a descriptive User-Agent (set on the httpx.Client by the caller,
from MB_USER_AGENT) and make at most 1 request per second.
"""

import time
from typing import Callable

import httpx

from app.cache import Cache, fetch_json
from app.ratelimit import RateLimiter

API_URL = "https://musicbrainz.org/ws/2/"

# The limit is 1/second. A little extra spacing absorbs network jitter, so two
# requests never *arrive* less than a second apart.
MB_MIN_INTERVAL = 1.1
RETRY_PAUSE = 3.0


class MusicBrainzError(Exception):
    pass


def parse_response(response: httpx.Response) -> dict:
    if response.status_code == 503:
        raise MusicBrainzError("MusicBrainz rate-limited us (HTTP 503). Wait a moment and retry.")
    response.raise_for_status()
    return response.json()


def parse_lookup(response: httpx.Response) -> dict:
    """Like parse_response, but "no such ID" (404, or 400 for a malformed ID)
    is a real answer: an empty dict, which also gets cached."""
    if response.status_code in (400, 404):
        return {}
    return parse_response(response)


class MusicBrainzClient:
    def __init__(self, cache: Cache, http: httpx.Client, limiter: RateLimiter | None = None, sleep=time.sleep):
        self.cache = cache
        self.http = http
        self.limiter = limiter or RateLimiter(MB_MIN_INTERVAL)
        self.sleep = sleep  # a parameter only so tests can skip the real pause

    def _get(self, path: str, params: dict, parse: Callable[[httpx.Response], dict] = parse_response) -> dict:
        # MusicBrainz also returns 503 when it's busy overall, even if we're
        # under our own limit, so retry once after a pause before giving up.
        for attempt in range(2):
            try:
                return fetch_json(self.cache, self.http, API_URL + path, params, limiter=self.limiter, parse=parse)
            except MusicBrainzError:
                if attempt == 1:
                    raise
                self.sleep(RETRY_PAUSE)
        return {}  # unreachable; keeps type checkers happy

    def search_release_groups(self, query: str, limit: int = 10) -> list[dict]:
        """Search release groups with a Lucene query string.

        Each result has "id", "title", "score" (0-100), "primary-type",
        "secondary-types", "first-release-date" and "artist-credit".
        """
        data = self._get("release-group", {"query": query, "fmt": "json", "limit": limit})
        return data.get("release-groups", [])

    def lookup_release_group(self, mbid: str) -> dict | None:
        """One release group by ID (same fields as a search result, minus
        "score"), or None if MusicBrainz doesn't know the ID."""
        data = self._get(f"release-group/{mbid}", {"inc": "artist-credits", "fmt": "json"}, parse=parse_lookup)
        return data or None
