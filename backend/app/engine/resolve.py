"""Resolve: turn a user's "Artist - Album" into one MusicBrainz release group.

Everything downstream is keyed by the release-group ID (mbid), because name
strings break on deluxe editions, remasters and duplicate titles.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.clients.musicbrainz import MusicBrainzClient

# MusicBrainz scores are relative: the top result is always 100, even when
# it's a bad match. So the score only ranks results; matches_input() below is
# what actually decides whether a result is the album the user meant.
MIN_SCORE = 80
# Among results within this many points of the best score, prefer studio albums.
SCORE_WINDOW = 10
# How alike two names must be (0-1) to count as the same. 0.75 allows small
# typos ("Playboy Carti" vs "Playboi Carti" is 0.92) but not different names.
MIN_NAME_SIMILARITY = 0.75

# Album titles people type when the album is named after the artist.
SELF_TITLED = {"self titled", "self-titled", "selftitled", "s/t"}

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
    than artist names do. "Artist - Self Titled" becomes ('Artist', 'Artist').
    """
    artist, sep, title = text.partition(" - ")
    artist, title = " ".join(artist.split()), " ".join(title.split())
    if not sep or not artist or not title:
        raise ValueError(f'Expected "Artist - Album", got: {text!r}')
    if title.lower() in SELF_TITLED:
        title = artist
    return artist, title


def _phrase(text: str) -> str:
    """Quote text as an exact Lucene phrase."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _fuzzy_terms(text: str) -> str:
    """Strip Lucene operators and mark each word fuzzy ("word~"), so small
    typos still match."""
    return " ".join(word + "~" for word in LUCENE_SPECIAL.sub(" ", text).split())


def _normalize(name: str) -> str:
    """Lowercase and turn punctuation into spaces, for comparing names."""
    return " ".join(re.sub(r"[^\w\s]", " ", name.lower()).split())


def similar(a: str, b: str) -> bool:
    # SequenceMatcher.ratio() is 1.0 for identical strings, 0.0 for nothing in common.
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio() >= MIN_NAME_SIMILARITY


def resolve_album(mb: MusicBrainzClient, artist: str, title: str) -> ResolvedAlbum | None:
    # Try an exact-phrase search first; if that finds nothing good (typos,
    # punctuation differences), fall back to a fuzzy word-based search.
    queries = [f"releasegroup:{_phrase(title)} AND artist:{_phrase(artist)}"]
    # Skip the fuzzy search when stripping leaves nothing, e.g. Sigur Rós - ( )
    if _fuzzy_terms(title) and _fuzzy_terms(artist):
        queries.append(f"releasegroup:({_fuzzy_terms(title)}) AND artist:({_fuzzy_terms(artist)})")
    for query in queries:
        best = pick_best(mb.search_release_groups(query), artist, title)
        if best is not None:
            return best
    return None


def matches_input(album: ResolvedAlbum, artist: str, title: str) -> bool:
    return similar(album.artist, artist) and similar(album.title, title)


def pick_best(results: list[dict], artist: str, title: str) -> ResolvedAlbum | None:
    candidates = [(int(r.get("score", 0)), r) for r in results]
    candidates = [(score, r) for score, r in candidates if matches_input(to_resolved(r), artist, title)]
    if not candidates:
        return None
    top_score = max(score for score, _ in candidates)
    close = [r for score, r in candidates if score >= max(MIN_SCORE, top_score - SCORE_WINDOW)]
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


# Album types people pick as inputs. Mixtapes are allowed; live albums,
# compilations and remixes aren't (they'd skew the tag profile).
SEARCH_EXCLUDED_TYPES = "compilation OR live OR remix OR dj-mix"
SEARCH_LIMIT = 8


def search_albums(mb: MusicBrainzClient, text: str) -> list[ResolvedAlbum]:
    """Autocomplete: albums matching free text like "carti whole lotta" or just
    "jane remover".

    The plain words search titles and artist names; the quoted artist:"..."^4
    part boosts albums whose artist name is exactly what was typed, so an
    artist name alone lists that artist's albums first.
    """
    words = " ".join(LUCENE_SPECIAL.sub(" ", text).split())
    if not words:
        return []
    query = (
        f'({words} OR artist:"{words}"^4) AND primarytype:album'
        f" AND NOT secondarytype:({SEARCH_EXCLUDED_TYPES})"
    )
    return [to_resolved(r) for r in mb.search_release_groups(query, limit=SEARCH_LIMIT)]


def album_by_id(mb: MusicBrainzClient, mbid: str) -> ResolvedAlbum | None:
    data = mb.lookup_release_group(mbid)
    return to_resolved(data) if data else None
