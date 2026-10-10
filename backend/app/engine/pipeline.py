"""The whole engine in one call: inputs -> ranked, explained recommendations.

Used by the CLI and the eval script (and later the API).
"""

from dataclasses import dataclass

from app.clients.lastfm import LastFmClient
from app.clients.musicbrainz import MusicBrainzClient
from app.engine.candidates import Candidate, enrich, gather_candidates
from app.engine.explain import reason
from app.engine.profile import Profile, album_tags, build_profile
from app.engine.resolve import ResolvedAlbum, resolve_album
from app.engine.score import WEIGHTS, Scored, rank, select_top


@dataclass
class Recommendation:
    album: ResolvedAlbum
    scored: Scored
    reason: str


@dataclass
class EngineResult:
    profile: Profile
    candidate_count: int
    recommendations: list[Recommendation]


def is_studio_album(album: ResolvedAlbum) -> bool:
    return album.primary_type == "Album" and not album.secondary_types


def recommend(
    lastfm: LastFmClient,
    mb: MusicBrainzClient,
    inputs: list[ResolvedAlbum],
    n: int = 5,
    weights: dict = WEIGHTS,
) -> EngineResult:
    # 1. Profile
    input_tags = [album_tags(lastfm, a.artist, a.title)[0] for a in inputs]
    profile = build_profile(input_tags)

    # 2. Candidates
    candidates = gather_candidates(lastfm, inputs, profile)
    enrich(lastfm, candidates)

    # 3. Score, then walk down the ranking keeping studio albums, one per artist
    ranked = rank(candidates, profile, n_inputs=len(inputs), weights=weights)
    input_ids = {a.mbid for a in inputs}

    def check(c: Candidate) -> ResolvedAlbum | None:
        album = resolve_album(mb, c.artist, c.title)
        if album is None or album.mbid in input_ids or not is_studio_album(album):
            return None
        return album

    picked = select_top(ranked, n, check)

    # 4. Explain
    input_artists = [a.artist for a in inputs]
    recs = [Recommendation(album=album, scored=s, reason=reason(s, profile, input_artists)) for s, album in picked]
    return EngineResult(profile=profile, candidate_count=len(candidates), recommendations=recs)
