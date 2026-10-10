import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.clients.musicbrainz import MusicBrainzError
from app.engine.candidates import Candidate
from app.engine.pipeline import EngineResult, Recommendation
from app.engine.profile import build_profile
from app.engine.score import score_candidate


def mbid(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def rg(n, title, artist="Artist"):
    return {"id": mbid(n), "title": title, "artist-credit": [{"name": artist}], "first-release-date": "2020-01-01",
            "primary-type": "Album", "secondary-types": []}


class FakeMB:
    def __init__(self, fail=False):
        self.fail = fail

    def search_release_groups(self, query, limit=10):
        if self.fail:
            raise MusicBrainzError("down")
        return [rg(1, "Souvlaki", "Slowdive")]

    def lookup_release_group(self, id):
        n = int(id.split("-")[-1])
        return rg(n, f"Album {n}") if n <= 10 else None  # IDs above 10 are "unknown"


def fake_recommend(lastfm, mb, inputs, n):
    profile = build_profile([[("shoegaze", 100)]])
    recs = []
    for i in range(n):
        album = main.ResolvedAlbum(mbid(100 + i), f"Rec {i}", "Ride", "1990", "Album", [])
        scored = score_candidate(Candidate("Ride", f"Rec {i}", tags=[("shoegaze", 100)]), profile, 5)
        recs.append(Recommendation(album=album, scored=scored, reason="shares the shoegaze of your picks"))
    return EngineResult(profile=profile, candidate_count=10, recommendations=recs, cluster_note=None)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "recommend", fake_recommend)
    app = main.create_app(main.Services(lastfm=None, mb=FakeMB()))
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_search(client):
    assert client.get("/search?q=s").json() == []  # too short to search
    [album] = client.get("/search?q=souvlaki").json()
    assert album["title"] == "Souvlaki" and album["artist"] == "Slowdive" and album["year"] == "2020"
    assert album["cover_url"].startswith("https://coverartarchive.org/release-group/")


def test_albums_lookup_keeps_order(client):
    found = client.get(f"/albums?ids={mbid(3)},{mbid(1)}").json()
    assert [a["title"] for a in found] == ["Album 3", "Album 1"]
    assert found[0]["mbid"] == mbid(3) and found[0]["cover_url"].endswith(mbid(3) + "/front-250")


@pytest.mark.parametrize("ids, status, message", [
    ("", 400, "between 1 and 5"),
    (",".join(mbid(i) for i in range(1, 7)), 400, "between 1 and 5"),
    ("not-an-id", 400, "Not a valid MusicBrainz ID"),
    (f"{mbid(1)},{mbid(1)}", 400, "more than once"),
    (f"{mbid(1)},{mbid(99)}", 404, "Unknown album ID"),
])
def test_albums_lookup_errors(client, ids, status, message):
    response = client.get(f"/albums?ids={ids}")
    assert response.status_code == status
    assert message in response.json()["detail"]


def test_recommend_success(client):
    body = client.post("/recommend", json={"album_ids": [mbid(i) for i in range(1, 6)]}).json()
    assert body["main"]["title"] == "Rec 0"
    assert len(body["runners_up"]) == 4
    assert body["main"]["listen_url"].startswith("https://www.youtube.com/results?search_query=Ride+Rec+0")
    assert body["cluster_note"] is None


@pytest.mark.parametrize("ids, status, message", [
    ([mbid(1), mbid(2)], 400, "exactly 5"),
    ([mbid(1)] * 5, 400, "more than once"),
    ([mbid(1), mbid(2), mbid(3), mbid(4), "not-an-id"], 400, "valid MusicBrainz ID"),
    ([mbid(1), mbid(2), mbid(3), mbid(4), mbid(99)], 404, "Unknown album"),
])
def test_recommend_errors(client, ids, status, message):
    response = client.post("/recommend", json={"album_ids": ids})
    assert response.status_code == status
    assert message in response.json()["detail"]


def test_upstream_failure_is_502():
    app = main.create_app(main.Services(lastfm=None, mb=FakeMB(fail=True)))
    with TestClient(app) as c:
        response = c.get("/search?q=souvlaki")
    assert response.status_code == 502
    assert "failed" in response.json()["detail"]
