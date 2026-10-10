import pytest

from app.engine.candidates import Candidate
from app.engine.profile import build_profile
from app.engine.resolve import ResolvedAlbum
from app.engine.score import cosine, popularity, rank, score_candidate, select_top


def test_cosine():
    assert cosine({"a": 1, "b": 1}, {"a": 2, "b": 2}) == pytest.approx(1.0)  # same proportions
    assert cosine({"a": 1}, {"b": 1}) == 0.0
    assert cosine({}, {"a": 1}) == 0.0
    assert 0 < cosine({"a": 1, "b": 1}, {"a": 1}) < 1


def test_popularity_is_log_scaled_and_capped():
    assert popularity(0) == 0.0
    assert popularity(999) == pytest.approx(3 / 7, abs=0.01)
    assert popularity(10**9) == 1.0
    assert popularity(1_000) < popularity(100_000) < popularity(2_000_000)


def test_score_formula():
    profile = build_profile([[("shoegaze", 100)], [("shoegaze", 100)]])
    c = Candidate("Ride", "Nowhere", pointed_by={"Slowdive"}, tags=[("shoegaze", 100)], listeners=999)
    s = score_candidate(c, profile, n_inputs=5)
    assert s.similarity == pytest.approx(1.0)
    assert s.pointers == pytest.approx(0.2)
    assert s.score == pytest.approx(1.0 + 0.2 - 3 / 7, abs=0.01)


def test_rank_orders_by_score():
    profile = build_profile([[("shoegaze", 100)]])
    good = Candidate("A", "x", tags=[("shoegaze", 100)])
    bad = Candidate("B", "y", tags=[("metal", 100)])
    assert [s.candidate.artist for s in rank([bad, good], profile, 5)] == ["A", "B"]


def _album(mbid):
    return ResolvedAlbum(mbid=mbid, title="t", artist="a", year=None, primary_type="Album", secondary_types=[])


def test_select_top_one_per_artist_and_skips_rejected():
    profile = build_profile([[("x", 100)]])
    cands = [
        Candidate("Ride", "Nowhere Live", tags=[("x", 100)]),  # best, but rejected by check
        Candidate("Ride", "Nowhere", tags=[("x", 90)]),  # Ride's next album gets a chance
        Candidate("Ride", "Going Blank Again", tags=[("x", 80)]),  # Ride already used
        Candidate("Lush", "Spooky", tags=[("x", 70)]),
    ]
    ranked = rank(cands, profile, 5)
    checked = []

    def check(c):
        checked.append(c.title)
        return None if "Live" in c.title else _album(c.title)

    picked = select_top(ranked, 2, check)
    assert [album.mbid for _, album in picked] == ["Nowhere", "Spooky"]
    assert "Going Blank Again" not in checked  # never paid an MB lookup for it


def test_rank_groups_by_artist_and_tries_most_listened_album_first():
    profile = build_profile([[("x", 100)]])
    cands = [
        Candidate("Future", "Deep Cut", tags=[("x", 100)], listeners=50_000),  # best tag match
        Candidate("Future", "DS2", tags=[("x", 80), ("y", 40)], listeners=2_000_000),
        Candidate("Other", "Album", tags=[("z", 100)], listeners=1_000),  # no tag match
    ]
    ranked = rank(cands, profile, 5)
    # Future's albums share the artist's popularity, so Deep Cut (perfect match)
    # still puts Future first; then DS2 is tried before Deep Cut.
    assert [s.candidate.title for s in ranked] == ["DS2", "Deep Cut", "Album"]
    assert ranked[0].popularity == ranked[1].popularity
