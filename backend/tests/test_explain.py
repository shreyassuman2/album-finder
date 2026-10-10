from app.engine.candidates import Candidate
from app.engine.explain import _join, reason
from app.engine.profile import build_profile
from app.engine.score import score_candidate

PROFILE = build_profile([
    [("shoegaze", 100), ("dream pop", 80)],
    [("shoegaze", 100), ("dream pop", 40), ("noise pop", 20)],
    [("post-rock", 100)],
])
INPUT_ARTISTS = ["Slowdive", "my bloody valentine", "Sigur Rós"]


def _reason(candidate):
    return reason(score_candidate(candidate, PROFILE, 3), PROFILE, INPUT_ARTISTS)


def test_join():
    assert _join(["a"]) == "a"
    assert _join(["a", "b"]) == "a and b"
    assert _join(["a", "b", "c"]) == "a, b and c"


def test_tags_and_artists():
    c = Candidate("Ride", "Nowhere", pointed_by={"my bloody valentine", "Slowdive"},
                  tags=[("noise pop", 100), ("shoegaze", 90), ("dream pop", 50)])
    # core tags (shoegaze, dream pop) come before the non-core noise pop; artists in input order
    assert _reason(c) == "shares the shoegaze and dream pop of your picks; similar to Slowdive and my bloody valentine"


def test_tags_only():
    c = Candidate("Mogwai", "Young Team", tags=[("post-rock", 100)])
    assert _reason(c) == "shares the post-rock of your picks"


def test_nothing_matched():
    assert _reason(Candidate("X", "Y", tags=[("metal", 100)])) == "close to the overall sound of your picks"
