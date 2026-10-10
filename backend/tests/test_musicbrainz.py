import httpx
import pytest

from app.cache import Cache
from app.clients.musicbrainz import MusicBrainzClient, MusicBrainzError
from app.ratelimit import RateLimiter


def _client(tmp_path, statuses):
    """MB client whose fake server answers with each status in turn."""
    calls = []

    def handler(request):
        status = statuses[len(calls)]
        calls.append(request)
        return httpx.Response(status, json={"release-groups": [{"id": "x"}]})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    mb = MusicBrainzClient(Cache(tmp_path / "c.db"), http, limiter=RateLimiter(0), sleep=lambda s: None)
    return mb, calls


def test_retries_once_after_503(tmp_path):
    mb, calls = _client(tmp_path, [503, 200])
    assert mb.search_release_groups("q") == [{"id": "x"}]
    assert len(calls) == 2


def test_gives_up_after_two_503s(tmp_path):
    mb, calls = _client(tmp_path, [503, 503])
    with pytest.raises(MusicBrainzError):
        mb.search_release_groups("q")
    assert len(calls) == 2
