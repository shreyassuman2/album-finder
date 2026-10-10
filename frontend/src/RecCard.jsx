import { useState } from 'react'
import { ArrowUpRight, Check, LinkSimple } from '@phosphor-icons/react'
import Cover from './Cover'

// "shares the rage of your picks" -> "Shares the rage of your picks"
const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1)

// The main pick is a big cover next to big type. Runners-up are a cover with
// a caption underneath. index staggers the entrance animation (n * 70ms).
export default function RecCard({ rec, main, index = 0 }) {
  const meta = `${rec.artist}${rec.year ? ` · ${rec.year}` : ''}`
  // Length of the longest word, so CSS can shrink a big title like
  // "PARTYNEXTDOOR" until it fits instead of breaking it mid-word.
  const longestWord = Math.max(...rec.title.split(/\s+/).map((w) => w.length))

  if (main) {
    return (
      <article className="rec-main">
        <div className="main-cover">
          <Cover album={rec} />
        </div>
        <div className="main-body">
          <div className="rec-label">Your sleeper pick</div>
          <h3 style={{ '--chars': longestWord }}>{rec.title}</h3>
          <div className="muted">{meta}</div>
          <p className="reason">{capitalize(rec.reason)}.</p>
          <div className="main-actions">
            <a className="listen-btn" href={rec.listen_url} target="_blank" rel="noreferrer">
              Listen <ArrowUpRight size={16} weight="bold" aria-hidden="true" />
            </a>
            <CopyLink />
          </div>
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

// Copies the current page address (which holds the 5 picks) to the clipboard.
// The label flips to "Link copied" for 2 seconds as feedback.
function CopyLink() {
  const [status, setStatus] = useState('idle') // 'idle' | 'copied' | 'failed'

  async function copy() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setStatus('copied')
    } catch {
      // Clipboard access can be blocked (old browsers, some privacy settings).
      setStatus('failed')
    }
    setTimeout(() => setStatus('idle'), 2000)
  }

  return (
    <button className="copy-link" onClick={copy} aria-live="polite">
      {status === 'copied' ? <Check size={16} weight="bold" aria-hidden="true" /> : <LinkSimple size={16} weight="bold" aria-hidden="true" />}
      {status === 'copied' ? 'Link copied' : status === 'failed' ? 'Copy the address bar instead' : 'Copy link'}
    </button>
  )
}
