"""Candidates: collect albums that might be good recommendations.

Two sources:
1. Similar artists of each input artist, and their top albums.
2. Last.fm's top albums for the profile's strongest tags.

Studio-album filtering happens later (score.select_top), because it needs a
MusicBrainz lookup per album at 1/second; we only pay that for albums that
rank high enough to matter.
"""

import re
from dataclasses import dataclass, field

from app.clients.lastfm import LastFmClient
from app.engine.profile import Profile, Tags, album_tags
from app.engine.resolve import ResolvedAlbum

SIMILAR_ARTISTS_PER_INPUT = 10
ALBUMS_PER_SIMILAR_ARTIST = 2
TAGS_USED = 3  # spec says 2-3 strongest core tags
ALBUMS_PER_TAG = 20

# "(Deluxe Edition)", "[2011 Remaster]" etc. Stripped so the title matches the
# original album on MusicBrainz.
EDITION_SUFFIX = re.compile(
    r"\s*[\(\[][^\)\]]*(deluxe|remaster|edition|expanded|anniversary|bonus)[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


@dataclass
class Candidate:
    artist: str
    title: str
    pointed_by: set[str] = field(default_factory=set)  # input artists whose similar-artist list led here
    from_tags: set[str] = field(default_factory=set)  # profile tags whose top-album list included it
    tags: Tags = field(default_factory=list)
    listeners: int = 0


def clean_title(title: str) -> str:
    return " ".join(EDITION_SUFFIX.sub("", title).split())


def _norm(name: str) -> str:
    return " ".join(name.lower().split())


def gather_candidates(lastfm: LastFmClient, inputs: list[ResolvedAlbum], profile: Profile) -> list[Candidate]:
    input_artists = {_norm(a.artist) for a in inputs}
    found: dict[tuple[str, str], Candidate] = {}  # keyed by normalized (artist, title) to merge duplicates

    def add(artist: str, title: str) -> Candidate | None:
        title = clean_title(title)
        if not title or title == "(null)" or _norm(artist) in input_artists:
            return None  # the input artists' own albums are never recommended
        key = (_norm(artist), _norm(title))
        if key not in found:
            found[key] = Candidate(artist=artist, title=title)
        return found[key]

    for album in inputs:
        for similar_artist, _match in lastfm.similar_artists(album.artist, limit=SIMILAR_ARTISTS_PER_INPUT):
            for title in lastfm.artist_top_albums(similar_artist, limit=ALBUMS_PER_SIMILAR_ARTIST):
                candidate = add(similar_artist, title)
                if candidate:
                    candidate.pointed_by.add(album.artist)

    for tag in profile.strongest(TAGS_USED):
        for artist, title in lastfm.tag_top_albums(tag, limit=ALBUMS_PER_TAG):
            candidate = add(artist, title)
            if candidate:
                candidate.from_tags.add(tag)

    return list(found.values())


def enrich(lastfm: LastFmClient, candidates: list[Candidate]) -> None:
    """Fetch tags and listener counts for each candidate (2 Last.fm calls each,
    cached after the first run)."""
    for c in candidates:
        c.tags, _source = album_tags(lastfm, c.artist, c.title)
        c.listeners = lastfm.album_listeners(c.artist, c.title)
