"""Profile: clean each album's Last.fm tags, then combine the 5 inputs into one
weighted tag profile."""

import re
from dataclasses import dataclass

from app.clients.lastfm import LastFmClient
from app.engine.stoptags import STOP_TAGS

# Last.fm tag counts are 0-100 relative to the top tag. Below this they're
# usually one-off noise from a single user.
MIN_TAG_COUNT = 5
# If an album has fewer clean tags than this, use the artist's tags instead.
MIN_ALBUM_TAGS = 3
# A tag carried by at least this many inputs is "core".
CORE_MIN_INPUTS = 2

# Matches a specific year like "1997" or "best of 2010", but not decades like
# "90s" or "1990s": \b needs a word boundary after the 4 digits, and there's
# none between "1990" and "s".
EXACT_YEAR = re.compile(r"\b(19|20)\d\d\b")

Tags = list[tuple[str, int]]  # [(tag, count 0-100)], strongest first


def _normalize_tag(name: str) -> str:
    return " ".join(name.lower().replace("-", " ").split())


def clean_tags(raw: Tags, artist_name: str = "") -> Tags:
    """Lowercase, treat hyphens as spaces ("hip-hop" = "hip hop"), drop stop
    tags / weak tags / bare numbers / exact years / the artist's own name, and
    merge duplicates. Returns [(tag, count)] strongest first."""
    artist_tag = _normalize_tag(artist_name)
    best: dict[str, int] = {}
    for name, count in raw:
        tag = _normalize_tag(name)
        if not tag or tag in STOP_TAGS or tag == artist_tag or count < MIN_TAG_COUNT:
            continue
        if tag.isdigit() or EXACT_YEAR.search(tag):  # "9" is a rating, "1997" a year
            continue
        best[tag] = max(count, best.get(tag, 0))
    return sorted(best.items(), key=lambda item: item[1], reverse=True)


def album_tags(lastfm: LastFmClient, artist: str, title: str) -> tuple[Tags, str]:
    """Returns (clean tags, source) where source is "album" or "artist"."""
    tags = clean_tags(lastfm.album_top_tags(artist, title), artist)
    if len(tags) >= MIN_ALBUM_TAGS:
        return tags, "album"
    return clean_tags(lastfm.artist_top_tags(artist), artist), "artist"


@dataclass
class Profile:
    weights: dict[str, int]  # tag -> how many inputs carry it
    strength: dict[str, float]  # tag -> sum of its counts/100 across inputs (tie-breaker)
    core: list[str]  # tags on CORE_MIN_INPUTS+ inputs, strongest first

    def strongest(self, k: int) -> list[str]:
        """Top k tags: core tags first (by how many inputs share them), then the rest."""
        ranked = sorted(self.weights, key=lambda t: (self.weights[t], self.strength[t]), reverse=True)
        return ranked[:k]


def build_profile(input_tags: list[Tags]) -> Profile:
    """Combine each input album's tags into one profile.

    A tag's weight is the number of inputs carrying it, so "shoegaze" on 3 of
    your 5 albums outweighs "ambient" on 1, however strongly that one album
    is tagged.
    """
    weights: dict[str, int] = {}
    strength: dict[str, float] = {}
    for tags in input_tags:
        for tag, count in tags:
            weights[tag] = weights.get(tag, 0) + 1
            strength[tag] = strength.get(tag, 0.0) + count / 100
    core = [t for t in weights if weights[t] >= CORE_MIN_INPUTS]
    core.sort(key=lambda t: (weights[t], strength[t]), reverse=True)
    return Profile(weights=weights, strength=strength, core=core)
