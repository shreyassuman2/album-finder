import { useState } from 'react'

// Album cover from the Cover Art Archive, or a placeholder if it has none
// (the image request fails, onError fires, and we swap in the placeholder).
export default function Cover({ album, size }) {
  const [missing, setMissing] = useState(false)
  const style = { width: size, height: size }
  if (missing) {
    return <div className="cover cover-missing" style={style} aria-label="No cover available">♪</div>
  }
  return (
    <img
      className="cover"
      style={style}
      src={album.cover_url}
      alt={`${album.title} cover`}
      loading="lazy"
      onError={() => setMissing(true)}
    />
  )
}
