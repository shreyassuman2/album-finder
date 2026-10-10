import Cover from './Cover'

// "shares the rage of your picks" -> "Shares the rage of your picks"
const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1)

export default function RecCard({ rec, main }) {
  return (
    <article className={main ? 'rec rec-main' : 'rec'}>
      <Cover album={rec} size={main ? 220 : 120} />
      <div className="rec-body">
        {main && <div className="rec-label">Your main pick</div>}
        <h3>{rec.title}</h3>
        <div className="muted">{rec.artist}{rec.year ? ` · ${rec.year}` : ''}</div>
        <p className="reason">{capitalize(rec.reason)}.</p>
        <a className="listen" href={rec.listen_url} target="_blank" rel="noreferrer">
          Listen ↗
        </a>
      </div>
    </article>
  )
}
