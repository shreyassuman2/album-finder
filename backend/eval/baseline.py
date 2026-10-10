"""A deliberately naive recommender, used only as a comparison point in the eval.

No tags, no scoring, no popularity penalty: walk each input's similar-artist
list in Last.fm's order (taking turns between the inputs) and recommend each
similar artist's most-played studio album. If the real engine can't beat this,
the scoring isn't earning its keep.
"""

from app.clients.lastfm import LastFmClient
from app.clients.musicbrainz import MusicBrainzClient
from app.engine.candidates import ALBUMS_PER_SIMILAR_ARTIST, SIMILAR_ARTISTS_PER_INPUT, clean_title
from app.engine.pipeline import is_studio_album
from app.engine.resolve import ResolvedAlbum, resolve_album


def similar_artists_baseline(
    lastfm: LastFmClient, mb: MusicBrainzClient, inputs: list[ResolvedAlbum], n: int = 20
) -> list[ResolvedAlbum]:
    input_artists = {a.artist.lower() for a in inputs}
    input_ids = {a.mbid for a in inputs}
    # Same similar-artist lists the engine uses (same params, so they come from the cache).
    lists = [[name for name, _ in lastfm.similar_artists(a.artist, limit=SIMILAR_ARTISTS_PER_INPUT)] for a in inputs]

    picks: list[ResolvedAlbum] = []
    seen: set[str] = set()
    # Round-robin: every input's #1 similar artist, then every input's #2, ...
    for rank in range(SIMILAR_ARTISTS_PER_INPUT):
        for names in lists:
            if rank >= len(names):
                continue
            artist = names[rank]
            if artist.lower() in seen or artist.lower() in input_artists:
                continue
            seen.add(artist.lower())
            # Their most-played album that is a real studio album (same filter as the engine).
            for title in lastfm.artist_top_albums(artist, limit=ALBUMS_PER_SIMILAR_ARTIST):
                album = resolve_album(mb, artist, clean_title(title))
                if album and album.mbid not in input_ids and is_studio_album(album):
                    picks.append(album)
                    break
            if len(picks) == n:
                return picks
    return picks
