"""Cover Art Archive: album covers by MusicBrainz release-group ID.

Docs: https://musicbrainz.org/doc/Cover_Art_Archive/API

We don't call this API from the backend. The URL below points straight at the
image (CAA redirects to the actual file), and the browser loads it. When an
album has no cover the image fails to load and the frontend shows a placeholder.
"""

COVER_SIZE = 250  # pixels; CAA serves 250, 500 and 1200 px thumbnails


def cover_url(mbid: str) -> str:
    return f"https://coverartarchive.org/release-group/{mbid}/front-{COVER_SIZE}"
