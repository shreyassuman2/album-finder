"""Last.fm API client: album/artist tags and similar artists.

Docs: https://www.last.fm/api
"""

from typing import Any

import httpx

from app.cache import Cache, fetch_json
from app.ratelimit import RateLimiter

API_URL = "https://ws.audioscrobbler.com/2.0/"

# Last.fm's terms ask for no more than 5 requests/second per IP (averaged over
# 5 minutes). 0.25s spacing = 4/s keeps us under that with some margin.
LASTFM_MIN_INTERVAL = 0.25

# Last.fm error code for "artist/album not found". That's a real answer, not a
# failure, so we return an empty result (and cache it) instead of raising.
NOT_FOUND = 6


class LastFmError(Exception):
    pass


def parse_response(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        raise LastFmError(f"Last.fm returned non-JSON (HTTP {response.status_code})")

    if "error" in data:
        if data["error"] == NOT_FOUND:
            return {}
        raise LastFmError(f"Last.fm error {data['error']}: {data.get('message', '')}")

    response.raise_for_status()
    return data


def _as_list(value: Any) -> list:
    """Last.fm returns a single dict instead of a one-item list when there's
    only one result, and may omit the field entirely when there are none."""
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    return value


class LastFmClient:
    def __init__(self, api_key: str, cache: Cache, http: httpx.Client, limiter: RateLimiter | None = None):
        self.api_key = api_key
        self.cache = cache
        self.http = http
        self.limiter = limiter or RateLimiter(LASTFM_MIN_INTERVAL)

    def _call(self, method: str, **params) -> dict:
        params = {
            "method": method,
            "api_key": self.api_key,
            "format": "json",
            "autocorrect": 1,  # let Last.fm fix small misspellings of names
            **params,
        }
        return fetch_json(self.cache, self.http, API_URL, params, limiter=self.limiter, parse=parse_response)

    def album_top_tags(self, artist: str, album: str) -> list[tuple[str, int]]:
        """[(tag, count)], count is 0-100 relative to the album's top tag."""
        data = self._call("album.gettoptags", artist=artist, album=album)
        tags = _as_list(data.get("toptags", {}).get("tag"))
        return [(t["name"], int(t.get("count", 0))) for t in tags]

    def artist_top_tags(self, artist: str) -> list[tuple[str, int]]:
        data = self._call("artist.gettoptags", artist=artist)
        tags = _as_list(data.get("toptags", {}).get("tag"))
        return [(t["name"], int(t.get("count", 0))) for t in tags]

    def artist_top_albums(self, artist: str, limit: int = 5) -> list[str]:
        """Album titles, most played first."""
        data = self._call("artist.gettopalbums", artist=artist, limit=limit)
        albums = _as_list(data.get("topalbums", {}).get("album"))
        return [a["name"] for a in albums]

    def tag_top_albums(self, tag: str, limit: int = 20) -> list[tuple[str, str]]:
        """[(artist, album title)] Last.fm ranks highest for this tag."""
        data = self._call("tag.gettopalbums", tag=tag, limit=limit)
        albums = _as_list(data.get("albums", {}).get("album"))
        return [(a["artist"]["name"], a["name"]) for a in albums]

    def album_listeners(self, artist: str, album: str) -> int:
        """How many Last.fm users have played this album (0 if unknown)."""
        data = self._call("album.getinfo", artist=artist, album=album)
        return int(data.get("album", {}).get("listeners", 0))

    def similar_artists(self, artist: str, limit: int = 20) -> list[tuple[str, float]]:
        """[(artist name, match)], match is 0-1, most similar first."""
        data = self._call("artist.getsimilar", artist=artist, limit=limit)
        artists = _as_list(data.get("similarartists", {}).get("artist"))
        return [(a["name"], float(a.get("match", 0))) for a in artists]
