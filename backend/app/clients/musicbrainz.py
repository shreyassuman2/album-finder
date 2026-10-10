"""MusicBrainz API client: release-group search.

Docs: https://musicbrainz.org/doc/MusicBrainz_API
Rules: send a descriptive User-Agent (set on the httpx.Client by the caller,
from MB_USER_AGENT) and make at most 1 request per second.
"""

import time

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


class MusicBrainzClient:
    def __init__(self, cache: Cache, http: httpx.Client, limiter: RateLimiter | None = None, sleep=time.sleep):
        self.cache = cache
        self.http = http
        self.limiter = limiter or RateLimiter(MB_MIN_INTERVAL)
        self.sleep = sleep  # a parameter only so tests can skip the real pause

    def search_release_groups(self, query: str, limit: int = 10) -> list[dict]:
        """Search release groups with a Lucene query string.

        Each result has "id", "title", "score" (0-100), "primary-type",
        "secondary-types", "first-release-date" and "artist-credit".
        """
        params = {"query": query, "fmt": "json", "limit": limit}
        # MusicBrainz also returns 503 when it's busy overall, even if we're
        # under our own limit, so retry once after a pause before giving up.
        for attempt in range(2):
            try:
                data = fetch_json(
                    self.cache, self.http, API_URL + "release-group", params, limiter=self.limiter, parse=parse_response
                )
                return data.get("release-groups", [])
            except MusicBrainzError:
                if attempt == 1:
                    raise
                self.sleep(RETRY_PAUSE)
        return []  # unreachable; keeps type checkers happy
