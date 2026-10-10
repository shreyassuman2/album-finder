"""Run the engine from the terminal.

Usage (from backend/):
    .venv/bin/python scripts/recommend_cli.py "Radiohead - OK Computer" "Slowdive - Souvlaki" ...
    .venv/bin/python scripts/recommend_cli.py --top 20 ...     # show more results
    .venv/bin/python scripts/recommend_cli.py --inputs-only ... # phase 1 view: tags and similar artists

The first run for new albums is slow (a minute or two) while the cache fills;
reruns take seconds.
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
from app.engine.pipeline import recommend  # noqa: E402
from app.engine.profile import album_tags  # noqa: E402
from app.engine.resolve import ResolvedAlbum, parse_input, resolve_album  # noqa: E402

TAGS_SHOWN = 15
SIMILAR_SHOWN = 10


def print_input_details(album: ResolvedAlbum, lastfm: LastFmClient) -> None:
    tags, source = album_tags(lastfm, album.artist, album.title)
    tag_text = ", ".join(f"{tag} {count}" for tag, count in tags[:TAGS_SHOWN]) or "(none)"
    print(f"   tags ({source}): {tag_text}")
    similar = lastfm.similar_artists(album.artist)
    similar_text = ", ".join(f"{name} {match:.2f}" for name, match in similar[:SIMILAR_SHOWN]) or "(none)"
    print(f"   similar:  {similar_text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recommend albums from 5 you love.")
    parser.add_argument("albums", nargs=5, metavar='"Artist - Album"')
    parser.add_argument("--top", type=int, default=5, help="how many recommendations to show (default 5)")
    parser.add_argument("--inputs-only", action="store_true", help="only show each input's tags and similar artists")
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
        try:
            run(args, inputs, mb, lastfm)
        except (httpx.HTTPError, LastFmError, MusicBrainzError) as e:
            print(f"\nupstream API error: {e}")
            return 1
        finally:
            cache.close()
    return 0


def run(args, inputs: list[tuple[str, str]], mb: MusicBrainzClient, lastfm: LastFmClient) -> None:
    print("Your albums:")
    resolved = []
    for n, (artist, title) in enumerate(inputs, start=1):
        album = resolve_album(mb, artist, title)
        if album is None:
            print(f"{n}. {artist} - {title}: could not resolve on MusicBrainz")
            continue
        print(f"{n}. {album.artist} - {album.title} ({album.year or '?'})")
        if args.inputs_only:
            print_input_details(album, lastfm)
        resolved.append(album)

    if args.inputs_only:
        return
    if len(resolved) < 5:
        print("\nNeed all 5 albums to resolve; fix the ones above and try again.")
        return

    result = recommend(lastfm, mb, resolved, n=args.top)
    core = ", ".join(f"{t} ({result.profile.weights[t]})" for t in result.profile.core) or "(none: your picks share no tags)"
    print(f"\nCore tags (number of your albums carrying each): {core}")
    print(f"Scored {result.candidate_count} candidate albums.\n")

    for i, rec in enumerate(result.recommendations):
        s = rec.scored
        label = "MAIN PICK" if i == 0 else f"#{i + 1}"
        print(f"{label}: {rec.album.artist} - {rec.album.title} ({rec.album.year or '?'})")
        print(f"   because: {rec.reason}")
        print(
            f"   score {s.score:+.3f}  (similarity {s.similarity:.2f}, pointers {s.pointers:.2f},"
            f" popularity {s.popularity:.2f} from {s.candidate.listeners:,} listeners)"
        )


if __name__ == "__main__":
    sys.exit(main())
