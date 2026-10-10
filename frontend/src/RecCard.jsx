import { ArrowUpRight } from '@phosphor-icons/react'
import Cover from './Cover'

// "shares the rage of your picks" -> "Shares the rage of your picks"
const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1)

// The main pick is a big cover next to big type. Runners-up are a cover with
// a caption underneath. index staggers the entrance animation (n * 70ms).
export default function RecCard({ rec, main, index = 0 }) {
  const meta = `${rec.artist}${rec.year ? ` · ${rec.year}` : ''}`

  if (main) {
    return (
      <article className="rec-main">
        <div className="main-cover">
          <Cover album={rec} />
        </div>
        <div className="main-body">
          <div className="rec-label">Your sleeper pick</div>
          <h3>{rec.title}</h3>
          <div className="muted">{meta}</div>
          <p className="reason">{capitalize(rec.reason)}.</p>
          <a className="listen-btn" href={rec.listen_url} target="_blank" rel="noreferrer">
            Listen <ArrowUpRight size={16} weight="bold" aria-hidden="true" />
          </a>
        </div>
      </article>
    )
  }

  return (
    <article className="runner" style={{ '--i': index }}>
      <a className="runner-cover" href={rec.listen_url} target="_blank" rel="noreferrer" aria-label={`Listen to ${rec.title}`}>
        <Cover album={rec} />
      </a>
      <h3>{rec.title}</h3>
      <div className="muted small">{meta}</div>
      <p className="reason small">{capitalize(rec.reason)}.</p>
      <a className="listen" href={rec.listen_url} target="_blank" rel="noreferrer">
        Listen <ArrowUpRight size={14} weight="bold" aria-hidden="true" />
      </a>
    </article>
  )
}
