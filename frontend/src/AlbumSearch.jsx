import { useEffect, useRef, useState } from 'react'
import { searchAlbums } from './api'
import Cover from './Cover'

const DEBOUNCE_MS = 400 // wait until typing pauses before searching
const MIN_LENGTH = 2
const SLOW_MS = 5000 // after this, explain the wait (the free server may be waking up)

export default function AlbumSearch({ onPick, disabled, excludeIds }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searchedFor, setSearchedFor] = useState('') // the query `results` belong to
  const [highlighted, setHighlighted] = useState(0)
  const [loading, setLoading] = useState(false)
  const [slow, setSlow] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const searching = query.trim().length >= MIN_LENGTH
  const shown = searching ? results : [] // hide old results once the query gets too short

  useEffect(() => {
    if (query.trim().length < MIN_LENGTH) return
    // Each keystroke restarts the timer, so we only search once typing
    // pauses. MusicBrainz allows 1 request/second, so this matters.
    const controller = new AbortController()
    let slowTimer
    const timer = setTimeout(async () => {
      setLoading(true)
      setError(null)
      slowTimer = setTimeout(() => setSlow(true), SLOW_MS)
      try {
        const found = await searchAlbums(query, controller.signal)
        setResults(found.filter((a) => !excludeIds.includes(a.mbid)))
        setSearchedFor(query)
        setHighlighted(0)
      } catch (err) {
        if (err.name !== 'AbortError') setError(err.message)
      } finally {
        clearTimeout(slowTimer)
        setSlow(false)
        setLoading(false)
      }
    }, DEBOUNCE_MS)
    // Runs when the query changes again: cancel the pending timer and any
    // request in flight, so an old, slow response can't overwrite a newer one.
    return () => {
      clearTimeout(timer)
      clearTimeout(slowTimer)
      controller.abort()
    }
  }, [query, excludeIds])

  function pick(album) {
    onPick(album)
    setQuery('')
    setResults([])
    inputRef.current?.focus()
  }

  function onKeyDown(e) {
    if (!shown.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => (h + 1) % shown.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => (h - 1 + shown.length) % shown.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      pick(shown[highlighted])
    } else if (e.key === 'Escape') {
      setResults([])
    }
  }

  return (
    <div className="search">
      <label className="search-label" htmlFor="album-search">
        Search for an album
      </label>
      <input
        id="album-search"
        ref={inputRef}
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder={disabled ? 'All 5 picked' : 'Artist and album, e.g. "frank ocean blonde"'}
        autoComplete="off"
      />
      {loading && (
        <div className="search-status">
          {slow ? 'Still searching… the server may be waking up, which can take up to a minute.' : 'Searching…'}
        </div>
      )}
      {error && <div className="search-status error">{error}</div>}
      {!loading && !error && searching && searchedFor === query && shown.length === 0 && (
        <div className="search-status">No albums found. Try adding the artist name.</div>
      )}
      {shown.length > 0 && (
        <ul className="search-results" role="listbox">
          {shown.map((album, i) => (
            <li
              key={album.mbid}
              role="option"
              aria-selected={i === highlighted}
              className={i === highlighted ? 'highlighted' : ''}
              onMouseEnter={() => setHighlighted(i)}
              onMouseDown={(e) => e.preventDefault()} // keep focus in the input
              onClick={() => pick(album)}
            >
              <Cover album={album} size={40} />
              <span className="result-text">
                <strong>{album.title}</strong>
                <span className="muted">{album.artist}{album.year ? ` · ${album.year}` : ''}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
