"""Resolve: turn a user's "Artist - Album" into one MusicBrainz release group.

Everything downstream is keyed by the release-group ID (mbid), because name
strings break on deluxe editions, remasters and duplicate titles.
"""

import re
from dataclasses import dataclass

from app.clients.musicbrainz import MusicBrainzClient

# MusicBrainz search scores are 0-100. Below this, it's probably not a match.
MIN_SCORE = 80
# Among results within this many points of the best score, prefer studio albums.
SCORE_WINDOW = 10

LUCENE_SPECIAL = re.compile(r'[+\-&|!(){}\[\]^"~*?:\\/]')


@dataclass
class ResolvedAlbum:
    mbid: str  # MusicBrainz release-group ID
    title: str
    artist: str
    year: str | None
    primary_type: str | None  # "Album", "EP", "Single", ...
    secondary_types: list[str]  # e.g. ["Live"], ["Compilation"]; empty for studio albums


def parse_input(text: str) -> tuple[str, str]:
    """'Radiohead - OK Computer' -> ('Radiohead', 'OK Computer').

    Splits on the first " - ", since album titles contain " - " more often
    than artist names do.
    """
    artist, sep, title = text.partition(" - ")
    artist, title = " ".join(artist.split()), " ".join(title.split())
    if not sep or not artist or not title:
        raise ValueError(f'Expected "Artist - Album", got: {text!r}')
    return artist, title


def _phrase(text: str) -> str:
    """Quote text as an exact Lucene phrase."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _terms(text: str) -> str:
    """Strip Lucene operators so text is searched as plain words."""
    return " ".join(LUCENE_SPECIAL.sub(" ", text).split())


def resolve_album(mb: MusicBrainzClient, artist: str, title: str) -> ResolvedAlbum | None:
    # Try an exact-phrase search first; if that finds nothing good (typos,
    # punctuation differences), fall back to a looser word-based search.
    queries = [f"releasegroup:{_phrase(title)} AND artist:{_phrase(artist)}"]
    # Skip the loose search when stripping leaves nothing, e.g. Sigur Rós - ( )
    if _terms(title) and _terms(artist):
        queries.append(f"releasegroup:({_terms(title)}) AND artist:({_terms(artist)})")
    for query in queries:
        best = pick_best(mb.search_release_groups(query))
        if best is not None:
            return best
    return None


def pick_best(results: list[dict]) -> ResolvedAlbum | None:
    if not results:
        return None
    top_score = max(int(r.get("score", 0)) for r in results)
    close = [r for r in results if int(r.get("score", 0)) >= max(MIN_SCORE, top_score - SCORE_WINDOW)]
    if not close:
        return None

    def preference(r: dict) -> tuple:
        is_album = r.get("primary-type") == "Album"
        is_studio = is_album and not r.get("secondary-types")
        # min() picks the smallest tuple, and False < True, so this ranks:
        # studio albums, then other albums (live etc.), then everything else.
        # Ties go to the higher search score.
        return (not is_studio, not is_album, -int(r.get("score", 0)))

    return to_resolved(min(close, key=preference))


def to_resolved(r: dict) -> ResolvedAlbum:
    # artist-credit is a list like [{"name": "Simon", "joinphrase": " & "}, {"name": "Garfunkel"}]
    artist = "".join(c.get("name", "") + c.get("joinphrase", "") for c in r.get("artist-credit", []))
    date = r.get("first-release-date") or ""
    return ResolvedAlbum(
        mbid=r["id"],
        title=r["title"],
        artist=artist,
        year=date[:4] or None,
        primary_type=r.get("primary-type"),
        secondary_types=list(r.get("secondary-types") or []),
    )
