"""Profile: per-album tags from Last.fm, cleaned up.

Phase 1 only fetches and cleans tags for one album at a time. The weighted
5-album profile and "core" tags come in phase 2.
"""

import re

from app.clients.lastfm import LastFmClient
from app.engine.resolve import ResolvedAlbum
from app.engine.stoptags import STOP_TAGS

# Last.fm tag counts are 0-100 relative to the top tag. Below this they're
# usually one-off noise from a single user.
MIN_TAG_COUNT = 5
# If an album has fewer clean tags than this, use the artist's tags instead.
MIN_ALBUM_TAGS = 3

# Matches a specific year like "1997" or "best of 2010", but not decades like
# "90s" or "1990s": \b needs a word boundary after the 4 digits, and there's
# none between "1990" and "s".
EXACT_YEAR = re.compile(r"\b(19|20)\d\d\b")


def clean_tags(raw: list[tuple[str, int]], artist_name: str = "") -> list[tuple[str, int]]:
    """Lowercase, collapse whitespace, drop stop tags / weak tags / exact years /
    the artist's own name, and merge duplicates. Returns [(tag, count)]
    strongest first."""
    artist_tag = " ".join(artist_name.lower().split())
    best: dict[str, int] = {}
    for name, count in raw:
        tag = " ".join(name.lower().split())
        if not tag or tag in STOP_TAGS or tag == artist_tag or count < MIN_TAG_COUNT:
            continue
        if EXACT_YEAR.search(tag):
            continue
        best[tag] = max(count, best.get(tag, 0))
    return sorted(best.items(), key=lambda item: item[1], reverse=True)


def album_tags(lastfm: LastFmClient, album: ResolvedAlbum) -> tuple[list[tuple[str, int]], str]:
    """Returns (clean tags, source) where source is "album" or "artist"."""
    tags = clean_tags(lastfm.album_top_tags(album.artist, album.title), album.artist)
    if len(tags) >= MIN_ALBUM_TAGS:
        return tags, "album"
    return clean_tags(lastfm.artist_top_tags(album.artist), album.artist), "artist"
