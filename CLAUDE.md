# Album Finder

A website where a user enters 5 albums they love and gets back 1 main recommendation + 4 runners-up, each with a one-line reason ("shares the shoegaze and dream pop of your picks; similar to Slowdive").

The recommendation engine is the core of this project. The website is a thin layer on top of it. When in doubt, spend effort on the engine and on measuring its quality, not on UI polish.

## About me (the developer)

- CS student, comfortable in Java, still building fluency in Python.
- I want to understand the code, not just have it. When you write something non-obvious (scoring math, async code, caching), add a short comment or explain it in your reply.
- Prefer simple, readable code over clever code. No unnecessary abstractions.

## Stack

| Layer | Choice |
| --- | --- |
| Engine + API | Python 3.11+, FastAPI, httpx |
| Cache | SQLite (stdlib `sqlite3`) |
| Frontend | React + Vite (plain JS or TS, no UI framework required) |
| Tests | pytest |
| Hosting (later) | Vercel (frontend), Render or Railway (backend) |

## Repo layout

```
album-finder/
  CLAUDE.md
  .env.example            # LASTFM_API_KEY, MB_USER_AGENT, CACHE_PATH
  backend/
    requirements.txt
    app/
      main.py             # FastAPI app: GET /search, POST /recommend
      config.py           # reads env vars
      cache.py            # SQLite response cache
      clients/
        lastfm.py
        musicbrainz.py
        coverart.py
      engine/
        resolve.py        # input -> MusicBrainz release-group + Last.fm artist/album
        profile.py        # build weighted tag profile from the 5 inputs
        candidates.py     # similar-artist + tag-based candidate generation
        score.py          # scoring + per-artist dedupe
        explain.py        # build the "because" line
        clusters.py       # handle inputs that don't agree
        stoptags.py       # junk tag list
    scripts/
      recommend_cli.py    # run the engine from the terminal
    eval/
      sets.json           # hand-written eval sets
      run_eval.py         # leave-one-out hit rate
    tests/
  frontend/
    (Vite React app)
```

Create files as they're needed; don't scaffold everything up front.

## Data sources and hard rules

- **Last.fm API**: tags, similar artists, top albums per artist and per tag, album search. Needs `LASTFM_API_KEY`.
- **MusicBrainz API**: canonical album identity (release groups) and release type filtering. Must send a descriptive `User-Agent` (from `MB_USER_AGENT`) and stay at or under 1 request/second. Use a simple rate limiter.
- **Cover Art Archive**: covers by MusicBrainz release-group ID. Show a placeholder when missing.
- **Do not** use Spotify's recommendations or related-artists endpoints (unavailable to new apps).
- **Do not** scrape Rate Your Music, Album of the Year, or any other site.
- **Every external API response goes through the SQLite cache.** Key by a normalized request (endpoint + sorted params). No direct HTTP calls that bypass `cache.py`.
- API keys live only in the backend `.env`. Never put them in frontend code or commit `.env`.
- Check each API's docs for current limits before changing request patterns.

## Engine spec

1. **Resolve**: match each input to one MusicBrainz release group. Key everything by release-group ID, not by name strings (deluxe editions, remasters and duplicate titles break name matching).
2. **Profile**: get each album's top tags from Last.fm; fall back to artist tags when an album has few. Lowercase and strip tags, drop anything in `stoptags.py` ("seen live", "albums i own", "favorite albums", etc.). Weight each tag by how many of the 5 inputs carry it. Tags on 2+ inputs are "core".
3. **Candidates**: for each input artist, take similar artists and their top albums. Add top albums for the 2-3 strongest core tags. Remove the input artists' own albums and anything that isn't a studio album (no live, compilation, single, EP).
4. **Score**:
   `score = w1 * cosine(candidate_tags, profile_tags) + w2 * (inputs_pointing_to_it / 5) - w3 * popularity`
   Start with equal weights in one config dict so they're easy to tune. Normalize popularity (e.g. log of Last.fm listeners scaled to 0-1). Keep only the best album per artist.
5. **Explain**: build the reason from the core tags the pick matched and the input artists that pointed to it. Template sentences only, no LLM. The reason must come from the actual score inputs.
6. **Disagreeing inputs**: if there are no core tags, cluster the inputs by tag overlap and recommend for the largest cluster. Return which cluster was used so the UI can say so.

Each engine step should be a plain function with clear inputs and outputs so it can be tested and run from the CLI.

## Evaluation

- `eval/sets.json` holds 8-10 sets of albums a real person likes (I'll write these).
- `run_eval.py` does leave-one-out: for each set, hide one album, feed 5 others, and record whether the hidden album appears in the top 20. Print overall hit rate and per-set results.
- Run the eval after any change to scoring, profiles, candidates or stop tags, and report the before/after hit rate.

## Build order (do not skip ahead)

1. **Data spike**: API clients + cache + `recommend_cli.py` that prints resolved albums, their cleaned tags, and similar artists for 5 inputs. Gate: tags look right for my own albums.
2. **Engine v0**: candidates, scoring, explain, stop tags, eval script. Gate: recommendations I'd actually play and a stable hit rate.
3. **Web app**: FastAPI endpoints, React UI (search with autocomplete, 5 slots, result cards with cover, reason, and a "Listen" link that opens a Spotify/YouTube *search URL*), clustering. Gate: works end to end.
4. **Ship and tune**: deploy, README with demo GIF, scoring formula and eval result.

Don't start the frontend until the engine works from the CLI.

## API contract

- `GET /search?q=...` -> list of `{ mbid, title, artist, year, cover_url }` for autocomplete.
- `POST /recommend` with `{ "album_ids": [5 MusicBrainz release-group IDs] }` -> `{ "main": Rec, "runners_up": [Rec x4], "cluster_note": str | null }` where `Rec = { mbid, title, artist, year, cover_url, reason, listen_url, score }`.
- Return clear errors for: fewer than 5 IDs, unknown IDs, upstream API failure.

## Out of scope for v1

User accounts, saved history, likes/dislikes, Spotify login or playlist export, AI-generated explanations, a native mobile app. Ask before adding any of these.

## Working conventions

- Run `pytest` before saying a task is done. Add tests for engine functions using cached/fixture data, not live API calls.
- Keep commits small and focused, with clear messages.
- If something in this file seems wrong or blocks progress, say so instead of working around it.
