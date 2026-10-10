"""Leave-one-out evaluation.

For each set of 6 albums in eval/sets.json: hide one, feed the other 5 to the
engine, and check whether the hidden album shows up in the top 20. Repeat for
each of the 6. A good engine should often "find" the album you left out.

Usage (from backend/):
    .venv/bin/python eval/run_eval.py

The first run is slow (many albums to fetch and cache); reruns are fast.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.cache import Cache  # noqa: E402
from app.clients.lastfm import LastFmClient  # noqa: E402
from app.clients.musicbrainz import MusicBrainzClient  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.engine.pipeline import recommend  # noqa: E402
from app.engine.resolve import parse_input, resolve_album  # noqa: E402

SETS_PATH = Path(__file__).resolve().parent / "sets.json"
TOP_N = 20
SET_SIZE = 6


def main() -> int:
    sets = json.loads(SETS_PATH.read_text())
    settings = load_settings()
    cache = Cache(settings.cache_path)

    total_hits = total_artist_hits = total_runs = 0
    with httpx.Client(headers={"User-Agent": settings.mb_user_agent}, timeout=15.0) as http:
        mb = MusicBrainzClient(cache, http)
        lastfm = LastFmClient(settings.lastfm_api_key, cache, http)

        for s in sets:
            print(f"\n== {s['name']} ==")
            if len(s["albums"]) != SET_SIZE:
                print(f"   skipped: needs exactly {SET_SIZE} albums, has {len(s['albums'])}")
                continue
            albums = [resolve_album(mb, *parse_input(text)) for text in s["albums"]]
            unresolved = [text for text, a in zip(s["albums"], albums) if a is None]
            if unresolved:
                print(f"   skipped: could not resolve {unresolved}")
                continue

            hits = artist_hits = 0
            for i, hidden in enumerate(albums):
                inputs = albums[:i] + albums[i + 1 :]
                recs = recommend(lastfm, mb, inputs, n=TOP_N).recommendations
                ids = [r.album.mbid for r in recs]
                artists = [r.album.artist.lower() for r in recs]

                if hidden.mbid in ids:
                    hits += 1
                    result = f"HIT at #{ids.index(hidden.mbid) + 1}"
                elif hidden.artist.lower() in artists:
                    # The engine keeps one album per artist, so it may have
                    # found the right artist but a different album.
                    result = f"artist only (#{artists.index(hidden.artist.lower()) + 1}, different album)"
                else:
                    result = "miss"
                if hidden.artist.lower() in artists:
                    artist_hits += 1
                print(f"   hide {hidden.artist} - {hidden.title}: {result}")

            print(f"   album hits {hits}/{SET_SIZE}, artist hits {artist_hits}/{SET_SIZE}")
            total_hits += hits
            total_artist_hits += artist_hits
            total_runs += SET_SIZE

    cache.close()
    if total_runs:
        print(f"\nOVERALL album hit rate: {total_hits}/{total_runs} = {total_hits / total_runs:.0%} (top {TOP_N})")
        print(f"OVERALL artist hit rate: {total_artist_hits}/{total_runs} = {total_artist_hits / total_runs:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
