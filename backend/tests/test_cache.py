import httpx
import pytest

from app.cache import Cache, fetch_json, make_key
from app.ratelimit import RateLimiter


def test_key_ignores_param_order_and_api_key():
    a = make_key("https://x/", {"b": 2, "a": 1, "api_key": "secret"})
    b = make_key("https://x/", {"a": 1, "b": 2})
    assert a == b
    assert "secret" not in a


def test_get_and_set_roundtrip(tmp_path):
    cache = Cache(tmp_path / "c.db")
    assert cache.get("k") is None
    cache.set("k", {"hello": [1, 2]})
    assert cache.get("k") == {"hello": [1, 2]}
    assert cache.get("k", max_age=-1) is None  # treated as expired


def _counting_client(handler):
    calls = []

    def wrapped(request):
        calls.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(wrapped)), calls


def test_second_fetch_is_served_from_cache(tmp_path):
    cache = Cache(tmp_path / "c.db")
    http, calls = _counting_client(lambda req: httpx.Response(200, json={"ok": True}))
    limiter = RateLimiter(0)

    for _ in range(2):
        data = fetch_json(cache, http, "https://x/", {"q": "a"}, limiter=limiter, parse=lambda r: r.json())
        assert data == {"ok": True}
    assert len(calls) == 1


def test_errors_are_not_cached(tmp_path):
    cache = Cache(tmp_path / "c.db")
    http, calls = _counting_client(lambda req: httpx.Response(500))
    limiter = RateLimiter(0)

    def parse(r):
        r.raise_for_status()
        return r.json()

    for _ in range(2):
        with pytest.raises(httpx.HTTPStatusError):
            fetch_json(cache, http, "https://x/", {"q": "a"}, limiter=limiter, parse=parse)
    assert len(calls) == 2
