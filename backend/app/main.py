"""FastAPI app: GET /search for autocomplete, GET /albums to look albums up by
ID (for shared links), POST /recommend for results.

Run (from backend/):
    .venv/bin/uvicorn app.main:create_app --factory --reload

(--factory tells uvicorn to call create_app() itself. That way importing this
module, e.g. from tests, doesn't need backend/.env.)

The endpoints are plain `def` (not `async def`), so FastAPI runs each request
on a worker thread. That's what we want: the clients block on HTTP calls and
the rate limiter, and a blocked thread doesn't hold up other requests.
"""

import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.cache import Cache
from app.clients.coverart import cover_url
from app.clients.lastfm import LastFmClient, LastFmError
from app.clients.musicbrainz import MusicBrainzClient, MusicBrainzError
from app.config import load_settings
from app.engine.pipeline import recommend
from app.engine.resolve import ResolvedAlbum, album_by_id, search_albums

INPUT_COUNT = 5
MIN_QUERY_LENGTH = 2
MBID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# ---- Response shapes (the API contract in CLAUDE.md) ----

class Album(BaseModel):
    mbid: str
    title: str
    artist: str
    year: str | None
    cover_url: str


class Rec(Album):
    reason: str
    listen_url: str
    score: float


class RecommendRequest(BaseModel):
    album_ids: list[str]


class RecommendResponse(BaseModel):
    main: Rec
    runners_up: list[Rec]
    cluster_note: str | None


def to_album(a: ResolvedAlbum) -> Album:
    return Album(mbid=a.mbid, title=a.title, artist=a.artist, year=a.year, cover_url=cover_url(a.mbid))


def clean_ids(raw: list[str]) -> list[str]:
    """Lowercase/strip IDs and reject duplicates or anything that isn't a
    MusicBrainz ID shape (400). Shared by /albums and /recommend."""
    ids = [i.strip().lower() for i in raw]
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "The same album was picked more than once.")
    malformed = [i for i in ids if not MBID_PATTERN.match(i)]
    if malformed:
        raise HTTPException(400, f"Not a valid MusicBrainz ID: {', '.join(malformed)}")
    return ids


def look_up(mb: MusicBrainzClient, ids: list[str]) -> list[ResolvedAlbum]:
    """Fetch each album (cached), or 404 naming the IDs MusicBrainz doesn't know."""
    albums = [album_by_id(mb, i) for i in ids]
    unknown = [i for i, a in zip(ids, albums) if a is None]
    if unknown:
        raise HTTPException(404, f"Unknown album ID(s): {', '.join(unknown)}")
    return albums


def listen_url(a: ResolvedAlbum) -> str:
    # A YouTube *search*, not a specific video: plays without any login, and
    # we never need a Spotify/YouTube API.
    return "https://www.youtube.com/results?search_query=" + quote_plus(f"{a.artist} {a.title} full album")


# ---- App setup ----

@dataclass
class Services:
    lastfm: LastFmClient
    mb: MusicBrainzClient


def create_app(services: Services | None = None, frontend_origins: list[str] | None = None) -> FastAPI:
    """Build the app. Tests pass fake `services`; normally they're created
    from backend/.env when the server starts."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services is not None:
            app.state.services = services
            yield
            return
        settings = load_settings()
        cache = Cache(settings.cache_path)
        http = httpx.Client(headers={"User-Agent": settings.mb_user_agent}, timeout=15.0)
        # One client each for the whole server, so every request shares the
        # same rate limiters (that's what keeps us under the API limits).
        app.state.services = Services(
            lastfm=LastFmClient(settings.lastfm_api_key, cache, http),
            mb=MusicBrainzClient(cache, http),
        )
        yield
        http.close()
        cache.close()

    app = FastAPI(title="Sleeper", lifespan=lifespan)
    if frontend_origins is None:
        frontend_origins = load_settings().frontend_origins if services is None else []
    app.add_middleware(CORSMiddleware, allow_origins=frontend_origins, allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.exception_handler(httpx.HTTPError)
    @app.exception_handler(LastFmError)
    @app.exception_handler(MusicBrainzError)
    def upstream_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": f"A music data service (Last.fm or MusicBrainz) failed: {exc}. Try again in a minute."},
        )

    @app.get("/health")
    def health() -> dict:
        """Cheap "are you up?" check. The frontend calls it on page load so a
        sleeping free-tier server starts waking up while the visitor picks albums."""
        return {"status": "ok"}

    @app.get("/search", response_model=list[Album])
    def search(request: Request, q: str = "") -> list[Album]:
        if len(q.strip()) < MIN_QUERY_LENGTH:
            return []
        return [to_album(a) for a in search_albums(request.app.state.services.mb, q)]

    @app.get("/albums", response_model=list[Album])
    def albums(request: Request, ids: str = "") -> list[Album]:
        """Look up to 5 albums by comma-separated ID, in the order given. The
        frontend uses this to refill the 5 slots when someone opens a shared link."""
        raw = [i for i in ids.split(",") if i.strip()]
        if not 1 <= len(raw) <= INPUT_COUNT:
            raise HTTPException(400, f"Pass between 1 and {INPUT_COUNT} album IDs (got {len(raw)}).")
        return [to_album(a) for a in look_up(request.app.state.services.mb, clean_ids(raw))]

    @app.post("/recommend", response_model=RecommendResponse)
    def recommend_albums(request: Request, body: RecommendRequest) -> RecommendResponse:
        s: Services = request.app.state.services
        if len(body.album_ids) != INPUT_COUNT:
            raise HTTPException(400, f"Pick exactly {INPUT_COUNT} albums (got {len(body.album_ids)}).")
        albums = look_up(s.mb, clean_ids(body.album_ids))

        result = recommend(s.lastfm, s.mb, albums, n=INPUT_COUNT)
        if not result.recommendations:
            raise HTTPException(422, "Couldn't find recommendations for these albums. Try swapping one out.")

        recs = [
            Rec(**to_album(r.album).model_dump(), reason=r.reason, listen_url=listen_url(r.album), score=round(r.scored.score, 3))
            for r in result.recommendations
        ]
        return RecommendResponse(main=recs[0], runners_up=recs[1:], cluster_note=result.cluster_note)

    return app

