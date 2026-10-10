"""Phase 1 data spike: resolve 5 albums and print their tags and similar artists.

Usage (from backend/):
    .venv/bin/python scripts/recommend_cli.py "Radiohead - OK Computer" "Slowdive - Souvlaki" ...
"""

import argparse
import sys
from pathlib import Path

# Lets this script import the `app` package from backend/ when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.cache import Cache  # noqa: E402
from app.clients.lastfm import LastFmClient, LastFmError  # noqa: E402
from app.clients.musicbrainz import MusicBrainzClient, MusicBrainzError  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.engine.profile import album_tags  # noqa: E402
from app.engine.resolve import parse_input, resolve_album  # noqa: E402

TAGS_SHOWN = 15
SIMILAR_SHOWN = 10


def print_album(n: int, artist: str, title: str, mb: MusicBrainzClient, lastfm: LastFmClient) -> None:
    print(f"\n{n}. {artist} - {title}")
    album = resolve_album(mb, artist, title)
    if album is None:
        print("   could not resolve on MusicBrainz")
        return

    kind = album.primary_type or "?"
    if album.secondary_types:
        kind += " + " + ", ".join(album.secondary_types)
    print(f"   resolved: {album.artist} - {album.title} ({album.year or '?'}) [{kind}]")
    print(f"   mbid:     {album.mbid}")

    tags, source = album_tags(lastfm, album)
    tag_text = ", ".join(f"{tag} {count}" for tag, count in tags[:TAGS_SHOWN]) or "(none)"
    print(f"   tags ({source}): {tag_text}")

    similar = lastfm.similar_artists(album.artist)
    similar_text = ", ".join(f"{name} {match:.2f}" for name, match in similar[:SIMILAR_SHOWN]) or "(none)"
    print(f"   similar:  {similar_text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve 5 albums and show their tags and similar artists.")
    parser.add_argument("albums", nargs=5, metavar='"Artist - Album"')
    args = parser.parse_args(argv)

    try:
        inputs = [parse_input(text) for text in args.albums]
    except ValueError as e:
        parser.error(str(e))

    settings = load_settings()
    cache = Cache(settings.cache_path)
    # One shared HTTP client. The User-Agent is required by MusicBrainz; we
    # send it to Last.fm too since it's good manners.
    with httpx.Client(headers={"User-Agent": settings.mb_user_agent}, timeout=15.0) as http:
        mb = MusicBrainzClient(cache, http)
        lastfm = LastFmClient(settings.lastfm_api_key, cache, http)
        for n, (artist, title) in enumerate(inputs, start=1):
            try:
                print_album(n, artist, title, mb, lastfm)
            except (httpx.HTTPError, LastFmError, MusicBrainzError) as e:
                print(f"   upstream API error: {e}")
    cache.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
