import httpx
import pytest

from app.cache import Cache
from app.clients.lastfm import LastFmClient, LastFmError, parse_response
from app.ratelimit import RateLimiter


def test_not_found_is_an_empty_result():
    assert parse_response(httpx.Response(404, json={"error": 6, "message": "Album not found"})) == {}


def test_other_errors_raise():
    with pytest.raises(LastFmError):
        parse_response(httpx.Response(200, json={"error": 10, "message": "Invalid API key"}))


def _client(tmp_path, body):
    http = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=body)))
    return LastFmClient("key", Cache(tmp_path / "c.db"), http, limiter=RateLimiter(0))


def test_single_tag_dict_is_handled(tmp_path):
    lastfm = _client(tmp_path, {"toptags": {"tag": {"name": "Shoegaze", "count": 100}}})
    assert lastfm.album_top_tags("Slowdive", "Souvlaki") == [("Shoegaze", 100)]


def test_similar_artists(tmp_path):
    body = {"similarartists": {"artist": [{"name": "Ride", "match": "1"}, {"name": "Lush", "match": "0.8"}]}}
    lastfm = _client(tmp_path, body)
    assert lastfm.similar_artists("Slowdive") == [("Ride", 1.0), ("Lush", 0.8)]
