import { useEffect, useMemo, useRef, useState } from 'react'
import { X } from '@phosphor-icons/react'
import AlbumSearch from './AlbumSearch'
import Cover from './Cover'
import RecCard from './RecCard'
import { getAlbums, getRecommendations, wakeServer } from './api'
import { EXAMPLES } from './examples'
import './App.css'

const SLOTS = 5

// Shared links look like  ?albums=id1,id2,id3,id4,id5
function sharedIds() {
  const param = new URLSearchParams(window.location.search).get('albums')
  return param ? param.split(',').filter(Boolean) : []
}

export default function App() {
  const [picks, setPicks] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // useMemo keeps the same array between renders unless picks change, so the
  // search box doesn't think its input changed and re-run the search.
  const pickedIds = useMemo(() => picks.map((a) => a.mbid), [picks])

  function addPick(album) {
    if (picks.length < SLOTS) setPicks([...picks, album])
  }

  function removePick(mbid) {
    setPicks(picks.filter((a) => a.mbid !== mbid))
  }

  async function recommend(ids = pickedIds) {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await getRecommendations(ids))
      // Put the picks in the address bar so this page can be shared or
      // bookmarked. replaceState changes the URL without reloading the page.
      window.history.replaceState(null, '', `?albums=${ids.join(',')}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fill all 5 slots from a list of IDs and recommend straight away. Used by
  // shared links and the example-set buttons.
  async function loadSet(ids, failMessage) {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const albums = await getAlbums(ids)
      setPicks(albums)
      await recommend(albums.map((a) => a.mbid))
    } catch (err) {
      setError(`${failMessage}: ${err.message}`)
      setLoading(false)
    }
  }

  // On page load: wake the server, and open the shared link if there is one.
  // In development React runs effects twice on purpose; the ref makes sure we
  // only do this once (refs survive that second run).
  const started = useRef(false)
  useEffect(() => {
    if (started.current) return
    started.current = true
    wakeServer()
    const ids = sharedIds()
    if (ids.length === 0) return
    if (ids.length !== SLOTS) {
      setError(`That link has ${ids.length} albums instead of ${SLOTS}. Pick your own below.`)
      return
    }
    loadSet(ids, "Couldn't open that shared link")
    // Empty list: run once, on page load.
  }, [])

  const slots = Array.from({ length: SLOTS }, (_, i) => picks[i])

  return (
    <div className="layout">
      {/* Left column: stays in view (sticky) on wide screens while results scroll. */}
      <aside className="picker">
        <div className="brand">Sleeper</div>
        <h1>Five albums you love.</h1>
        <p className="lede">We'll find an album you'll enjoy, plus four more worth a listen.</p>
        <div className="examples">
          <span className="muted small">Or try a set:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex.name} className="example" onClick={() => loadSet(ex.ids, "Couldn't load that set")} disabled={loading}>
              {ex.name}
            </button>
          ))}
        </div>

        <AlbumSearch onPick={addPick} disabled={picks.length >= SLOTS} excludeIds={pickedIds} />

        <div className="slots-head">
          <span>Your picks</span>
          <span className="mono">{picks.length}/{SLOTS}</span>
        </div>
        <ol className="slots">
          {slots.map((album, i) => (
            <li key={album ? album.mbid : `empty-${i}`} className={album ? 'slot' : 'slot slot-empty'}>
              <span className="slot-num mono">{i + 1}</span>
              {album ? (
                <>
                  <Cover album={album} size={48} />
                  <span className="slot-text">
                    <strong>{album.title}</strong>
                    <span className="muted">{album.artist}</span>
                  </span>
                  <button className="remove" onClick={() => removePick(album.mbid)} aria-label={`Remove ${album.title}`}>
                    <X size={16} weight="bold" />
                  </button>
                </>
              ) : (
                <>
                  <span className="slot-placeholder" />
                  <span className="muted">Empty</span>
                </>
              )}
            </li>
          ))}
        </ol>

        <button className="go" onClick={() => recommend()} disabled={picks.length < SLOTS || loading}>
          {loading ? 'Finding albums…' : 'Get recommendations'}
        </button>
        {loading && (
          <p className="muted small">
            New albums can take a minute or two while music data downloads (longer if the server was asleep).
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </aside>

      {/* Right column: an empty state, a loading skeleton, or the results. */}
      <main className="stage">
        {loading && <ResultsSkeleton />}
        {!loading && !result && <EmptyStage />}
        {result && (
          <section className="results">
            {result.cluster_note && <p className="cluster-note">{result.cluster_note}</p>}
            <RecCard rec={result.main} main />
            {result.runners_up.length > 0 && (
              <>
                <h2>Runners-up</h2>
                <div className="runners-up">
                  {result.runners_up.map((rec, i) => (
                    <RecCard key={rec.mbid} rec={rec} index={i + 1} />
                  ))}
                </div>
              </>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

// What the right column shows before any results: outlines of where the
// main pick and the runners-up will land.
function EmptyStage() {
  return (
    <div className="empty-stage">
      <div className="empty-main">
        <p>Your pick shows up here.</p>
        <p className="muted small">Add five albums, then get recommendations.</p>
      </div>
      <div className="empty-row">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="empty-tile" />
        ))}
      </div>
    </div>
  )
}

// Grey blocks in the same shape as the results (1 main + 4 runners-up),
// shown while the engine works, so the page doesn't jump when results arrive.
// aria-hidden: the button already says it's loading.
function ResultsSkeleton() {
  return (
    <section className="results" aria-hidden="true">
      <div className="rec-main">
        <div className="sk sk-square" />
        <div className="sk-lines">
          <div className="sk sk-line w30" />
          <div className="sk sk-title" />
          <div className="sk sk-line w40" />
          <div className="sk sk-line w90" />
          <div className="sk sk-line w70" />
        </div>
      </div>
      <div className="runners-up">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="runner">
            <div className="sk sk-square" />
            <div className="sk sk-line w70" />
            <div className="sk sk-line w40" />
          </div>
        ))}
      </div>
    </section>
  )
}
