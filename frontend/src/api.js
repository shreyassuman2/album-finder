// Talks to the FastAPI backend. In development, /api is forwarded to it by the
// Vite dev server (see vite.config.js). When deployed, set VITE_API_URL to the
// backend's address.
const API_URL = import.meta.env.VITE_API_URL || '/api'
const UNREACHABLE = "Can't reach the server. Is the backend running?"

async function request(path, options) {
  let response
  try {
    response = await fetch(API_URL + path, options)
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new Error(UNREACHABLE)
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    // Our backend always explains its errors in `detail`. A 5xx without one
    // comes from the dev proxy: the backend isn't answering at all.
    if (!body.detail && response.status >= 500) throw new Error(UNREACHABLE)
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  return body
}

export function searchAlbums(query, signal) {
  return request('/search?q=' + encodeURIComponent(query), { signal })
}

// Albums by ID, in the same order. Used to refill the slots from a shared link.
export function getAlbums(albumIds) {
  return request('/albums?ids=' + albumIds.map(encodeURIComponent).join(','))
}

export function getRecommendations(albumIds) {
  return request('/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ album_ids: albumIds }),
  })
}
