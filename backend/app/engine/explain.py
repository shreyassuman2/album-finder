"""Explain: the one-line "because" for a recommendation.

Built only from the score inputs (matched tags and the input artists that
pointed to it), so the reason is always true to why the album ranked.
"""

from app.engine.profile import Profile
from app.engine.score import Scored

MAX_TAGS = 2
MAX_ARTISTS = 2


def _join(items: list[str]) -> str:
    """["a"] -> "a", ["a", "b"] -> "a and b", ["a", "b", "c"] -> "a, b and c"."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def matched_tags(s: Scored, profile: Profile) -> list[str]:
    """Candidate tags that are also in the profile: core tags first, then by
    how much they contributed to the similarity score."""
    candidate_tags = dict(s.candidate.tags)
    shared = [t for t in candidate_tags if t in profile.weights]
    shared.sort(key=lambda t: (t in profile.core, profile.weights[t] * candidate_tags[t]), reverse=True)
    return shared[:MAX_TAGS]


def reason(s: Scored, profile: Profile, input_artist_order: list[str]) -> str:
    tags = matched_tags(s, profile)
    # Keep artists in the order the user entered them, so the line is stable.
    artists = [a for a in input_artist_order if a in s.candidate.pointed_by][:MAX_ARTISTS]

    parts = []
    if tags:
        parts.append(f"shares the {_join(tags)} of your picks")
    if artists:
        parts.append(f"similar to {_join(artists)}")
    if not parts:
        return "close to the overall sound of your picks"
    return "; ".join(parts)
