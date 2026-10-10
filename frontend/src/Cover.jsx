import { useState } from 'react'
import { MusicNote } from '@phosphor-icons/react'

// Album cover from the Cover Art Archive, or a placeholder if it has none
// (the image request fails, onError fires, and we swap in the placeholder).
// Without a size, the cover fills its container and CSS decides how big it is.
export default function Cover({ album, size }) {
  const [missing, setMissing] = useState(false)
  const style = size ? { width: size, height: size } : undefined
  if (missing) {
    return (
      <div className="cover cover-missing" style={style} aria-label="No cover available">
        <MusicNote size={size ? Math.round(size * 0.4) : 40} />
      </div>
    )
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
