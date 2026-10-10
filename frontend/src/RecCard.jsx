import Cover from './Cover'

// "shares the rage of your picks" -> "Shares the rage of your picks"
const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1)

// index staggers the entrance animation: card n starts n * 80ms after the first.
export default function RecCard({ rec, main, index = 0 }) {
  return (
    <article className={main ? 'rec rec-main' : 'rec'} style={{ '--i': index }}>
      {main ? (
        // The main pick gets a record that slides out from behind its sleeve.
        <div className="cover-wrap">
          <div className="mini-vinyl" aria-hidden="true" />
          <Cover album={rec} size={220} />
        </div>
      ) : (
        <Cover album={rec} size={120} />
      )}
      <div className="rec-body">
        {main && <div className="rec-label">Your sleeper pick</div>}
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
