"""The whole engine in one call: inputs -> ranked, explained recommendations.

Used by the CLI, the eval script and the API.
"""

from dataclasses import dataclass

from app.clients.lastfm import LastFmClient
from app.clients.musicbrainz import MusicBrainzClient
from app.engine.candidates import SIMILAR_ARTISTS_PER_INPUT, Candidate, enrich, gather_candidates
from app.engine.clusters import cluster_inputs, cluster_note
from app.engine.explain import reason
from app.engine.profile import Profile, album_tags, build_profile
from app.engine.resolve import ResolvedAlbum, resolve_album
from app.engine.score import WEIGHTS, Scored, rank, select_top

NO_OVERLAP_NOTE = "Your picks don't have much in common, so these draw on all of them."


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
    cluster_note: str | None = None  # set when we only used some of the inputs


def is_studio_album(album: ResolvedAlbum) -> bool:
    return album.primary_type == "Album" and not album.secondary_types


def recommend(
    lastfm: LastFmClient,
    mb: MusicBrainzClient,
    inputs: list[ResolvedAlbum],
    n: int = 5,
    weights: dict = WEIGHTS,
) -> EngineResult:
    all_inputs = inputs

    # 1. Profile
    input_tags = [album_tags(lastfm, a.artist, a.title)[0] for a in inputs]
    profile = build_profile(input_tags)

    # 1b. If the inputs split into unrelated groups (say 2 rap, 2 jazz and a
    #     shoegaze album), recommend for the biggest group instead of
    #     averaging unrelated sounds together. Checked every time, not only
    #     when there are no core tags: rap and jazz can each be "core" (on 2
    #     inputs) while the 5 picks still don't agree.
    note = None
    similar = [
        {name.lower() for name, _ in lastfm.similar_artists(a.artist, limit=SIMILAR_ARTISTS_PER_INPUT)}
        for a in inputs
    ]
    biggest = cluster_inputs(inputs, input_tags, similar)[0]
    if len(biggest) == 1:
        note = NO_OVERLAP_NOTE
    elif len(biggest) < len(inputs):
        inputs = [inputs[i] for i in biggest]
        input_tags = [input_tags[i] for i in biggest]
        profile = build_profile(input_tags)
        note = cluster_note(inputs)

    # 2. Candidates (never any album by an artist from *any* of the inputs)
    candidates = gather_candidates(lastfm, inputs, profile, exclude=all_inputs)
    enrich(lastfm, candidates)

    # 3. Score, then walk down the ranking keeping studio albums, one per artist
    ranked = rank(candidates, profile, n_inputs=len(inputs), weights=weights)
    input_ids = {a.mbid for a in all_inputs}

    def check(c: Candidate) -> ResolvedAlbum | None:
        album = resolve_album(mb, c.artist, c.title)
        if album is None or album.mbid in input_ids or not is_studio_album(album):
            return None
        return album

    picked = select_top(ranked, n, check)

    # 4. Explain
    input_artists = [a.artist for a in inputs]
    recs = [Recommendation(album=album, scored=s, reason=reason(s, profile, input_artists)) for s, album in picked]
    return EngineResult(profile=profile, candidate_count=len(candidates), recommendations=recs, cluster_note=note)
