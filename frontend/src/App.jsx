import { useMemo, useState } from 'react'
import { X } from '@phosphor-icons/react'
import AlbumSearch from './AlbumSearch'
import Background from './Background'
import Cover from './Cover'
import RecCard from './RecCard'
import { getRecommendations } from './api'
import './App.css'

const SLOTS = 5

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

  async function recommend() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await getRecommendations(pickedIds))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const slots = Array.from({ length: SLOTS }, (_, i) => picks[i])

  return (
    <>
    <Background />
    <main>
      <header>
        <h1>Sleeper</h1>
        <p className="muted">Pick 5 albums you love. Get one you'll love next, plus 4 runners-up.</p>
      </header>

      <section className="picker">
        <AlbumSearch onPick={addPick} disabled={picks.length >= SLOTS} excludeIds={pickedIds} />
        <ol className="slots">
          {slots.map((album, i) => (
            <li key={album ? album.mbid : `empty-${i}`} className={album ? 'slot' : 'slot slot-empty'}>
              {album ? (
                <>
                  <Cover album={album} size={56} />
                  <span className="slot-text">
                    <strong>{album.title}</strong>
                    <span className="muted">{album.artist}</span>
                  </span>
                  <button className="remove" onClick={() => removePick(album.mbid)} aria-label={`Remove ${album.title}`}>
                    <X size={18} weight="bold" />
                  </button>
                </>
              ) : (
                <span className="muted">Album {i + 1}</span>
              )}
            </li>
          ))}
        </ol>
        <button className="go" onClick={recommend} disabled={picks.length < SLOTS || loading}>
          {loading ? (
            <>
              <span className="eq" aria-hidden="true"><i /><i /><i /><i /></span>
              Finding albums…
            </>
          ) : (
            'Get recommendations'
          )}
        </button>
        {loading && (
          <p className="muted small">
            New albums can take a minute or two while music data downloads (longer if the server was asleep).
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      {loading && <ResultsSkeleton />}

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
    </>
  )
}

// Grey placeholder cards in the same shape as the results (1 main + 4
// runners-up), shown while the engine works, so the page doesn't jump when
// the real cards arrive. aria-hidden: the button already says it's loading.
function ResultsSkeleton() {
  const lines = (
    <div className="sk-lines">
      <div className="sk sk-title" />
      <div className="sk sk-line w40" />
      <div className="sk sk-line w90" />
      <div className="sk sk-line w70" />
    </div>
  )
  return (
    <section className="results" aria-hidden="true">
      <div className="rec rec-main skeleton">
        <div className="sk sk-cover" />
        {lines}
      </div>
      <div className="runners-up">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rec skeleton" style={{ '--i': i }}>
            <div className="sk sk-cover" />
            {lines}
          </div>
        ))}
      </div>
    </section>
  )
}
