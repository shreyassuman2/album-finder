"""Score: rank candidates, then keep the best studio album per artist.

score = w1 * cosine(candidate_tags, profile_tags)
      + w2 * (inputs_pointing_to_it / 5)
      - w3 * popularity
"""

import math
from dataclasses import dataclass
from typing import Callable

from app.engine.candidates import Candidate
from app.engine.profile import Profile
from app.engine.resolve import ResolvedAlbum

# All three start equal, as the spec says. Tune these against the eval.
WEIGHTS = {
    "similarity": 1.0,  # w1: tag overlap with your profile
    "pointers": 1.0,  # w2: how many of your artists' similar-artist lists led here
    "popularity": 1.0,  # w3: penalty for very popular albums
}

# 10 million listeners counts as maximally popular (popularity = 1.0).
MAX_LOG_LISTENERS = 7


@dataclass
class Scored:
    candidate: Candidate
    similarity: float
    pointers: float
    popularity: float
    score: float


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity of two tag->weight vectors: 1.0 means the same mix of
    tags in the same proportions, 0.0 means no tags in common.

    It's the dot product divided by both lengths, so an album with many tags
    isn't favored just for having more of them.
    """
    dot = sum(weight * b[tag] for tag, weight in a.items() if tag in b)
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def popularity(listeners: int) -> float:
    """Listener count squashed to 0-1 on a log scale.

    The log matters: going from 1k to 10k listeners and from 1M to 10M are
    the same step (+1/7). Without it, every album under ~1M would look
    equally obscure.
      1,000 -> 0.43   100,000 -> 0.71   2,000,000 -> 0.90
    """
    return min(1.0, math.log10(listeners + 1) / MAX_LOG_LISTENERS)


def score_candidate(
    c: Candidate, profile: Profile, n_inputs: int, weights: dict = WEIGHTS, listeners: int | None = None
) -> Scored:
    """`listeners` overrides the album's own count (rank() passes the artist's)."""
    similarity = cosine(dict(c.tags), profile.weights)
    pointers = len(c.pointed_by) / n_inputs
    pop = popularity(c.listeners if listeners is None else listeners)
    total = weights["similarity"] * similarity + weights["pointers"] * pointers - weights["popularity"] * pop
    return Scored(candidate=c, similarity=similarity, pointers=pointers, popularity=pop, score=total)


def rank(candidates: list[Candidate], profile: Profile, n_inputs: int, weights: dict = WEIGHTS) -> list[Scored]:
    """Order candidates so select_top can walk them top-down.

    Popularity is judged per artist (by their most-played album), so it
    decides *which artists* we suggest, not which of an artist's albums.
    Artists are ordered by their best album's score; within an artist, their
    most-listened album comes first, since that's the natural place to start
    with an artist you don't know yet.
    """
    artist_listeners: dict[str, int] = {}
    for c in candidates:
        key = c.artist.lower()
        artist_listeners[key] = max(artist_listeners.get(key, 0), c.listeners)

    scored = [
        score_candidate(c, profile, n_inputs, weights, listeners=artist_listeners[c.artist.lower()])
        for c in candidates
    ]

    artist_best: dict[str, float] = {}
    for s in scored:
        key = s.candidate.artist.lower()
        artist_best[key] = max(artist_best.get(key, -math.inf), s.score)

    return sorted(scored, key=lambda s: (artist_best[s.candidate.artist.lower()], s.candidate.listeners), reverse=True)


def select_top(
    ranked: list[Scored],
    n: int,
    check: Callable[[Candidate], ResolvedAlbum | None],
) -> list[tuple[Scored, ResolvedAlbum]]:
    """Walk the ranking from the top, keeping the best album per artist.

    `check` resolves a candidate on MusicBrainz and returns it only if it's an
    acceptable studio album (else None). It's slow (1 req/s), so it's only
    called on albums we might actually return, and on nothing past the top n.
    If an artist's best album fails the check, their next one still gets a chance.
    """
    picked: list[tuple[Scored, ResolvedAlbum]] = []
    artists_used: set[str] = set()
    for s in ranked:
        if len(picked) >= n:
            break
        artist = s.candidate.artist.lower()
        if artist in artists_used:
            continue
        album = check(s.candidate)
        if album is None:
            continue
        picked.append((s, album))
        artists_used.add(artist)
    return picked
