import { useEffect } from 'react'
import { ArrowLeft, ArrowRight, ArrowUpRight } from '@phosphor-icons/react'
import Cover from './Cover'

const REPO_URL = 'https://github.com/shreyassuman2/sleeper'
const API_DOCS_URL = 'https://album-finder-api.onrender.com/docs'

// A real example for the diagram at the top: the R&B example set and the
// album Sleeper actually picked for it. Covers load from the Cover Art Archive.
const coverOf = (mbid, title) => ({ title, cover_url: `https://coverartarchive.org/release-group/${mbid}/front-250` })
const DEMO_INPUTS = [
  coverOf('0da340a0-6ad7-4fc2-a272-6f94393a7831', 'Blonde'),
  coverOf('ba660007-8e88-4301-ba89-5574d06d29cc', 'Freudian'),
  coverOf('47809021-4515-4215-beea-db3f5dfb6267', 'Take Care'),
  coverOf('8f892c1b-0709-4cf4-9711-493892a9eb9b', 'Ctrl'),
  coverOf('52859a02-4538-4e5c-b484-7d179f4c6ff6', 'WASTELAND'),
]
const DEMO_PICK = coverOf('c5597cfa-22d6-42bf-9eec-5fe457ffe427', 'PARTYNEXTDOOR')

const ENDPOINTS = [
  ['GET', '/search?q=…', 'Album autocomplete'],
  ['GET', '/albums?ids=…', 'Look up albums by ID (used by shared links)'],
  ['POST', '/recommend', 'Five album IDs in, five recommendations out'],
  ['GET', '/health', 'Wakes the server when the page opens'],
]

const STACK = ['Python', 'FastAPI', 'SQLite', 'httpx', 'pytest', 'React', 'Vite', 'GitHub Actions']

const STEPS = [
  ['Match', 'Each album you pick is matched to one MusicBrainz entry, so deluxe editions and remasters count as the same record.'],
  ['Profile', 'Last.fm tags from your five albums become a taste profile. Tags that two or more of your picks share count the most.'],
  ['Gather', "Candidates come from artists similar to yours and from top albums in your strongest tags. Your own artists are left out."],
  ['Score', 'Each candidate is scored on how closely its tags match yours and how many of your artists point to it. Very popular artists lose a few points, so lesser-known ones get a chance.'],
  ['Explain', "The one-line reason is built from the same tags and artists that produced the score. There's no AI-written text."],
]

// The About page (shown at /#about). Plain content, no data fetching.
export default function About() {
  // Start at the top, not wherever the picker page was scrolled to.
  useEffect(() => window.scrollTo(0, 0), [])

  return (
    <div className="about">
      <nav className="topbar">
        <a className="brand" href="#">Sleeper</a>
        <a className="nav-link" href="#">
          <ArrowLeft size={16} weight="bold" aria-hidden="true" /> Back to picks
        </a>
      </nav>

      <h1>About Sleeper</h1>
      <p className="about-lede">
        Pick five albums you love. Sleeper finds one to play next, plus four more, each with a short reason why.
      </p>

      {/* 5 covers in, 1 out: the whole idea in one picture. */}
      <figure className="demo">
        <div className="demo-inputs">
          {DEMO_INPUTS.map((album, i) => (
            <div key={album.title} className="demo-in" style={{ '--i': i }}>
              <Cover album={album} />
            </div>
          ))}
        </div>
        <ArrowRight className="demo-arrow" size={28} weight="bold" aria-hidden="true" />
        <div className="demo-out">
          <Cover album={DEMO_PICK} />
        </div>
        <figcaption className="muted small">
          A real run: Blonde, Freudian, Take Care, Ctrl and WASTELAND in, PARTYNEXTDOOR out.
        </figcaption>
      </figure>

      <section>
        <h2>How it works</h2>
        <ol className="steps">
          {STEPS.map(([name, text], i) => (
            <li key={name}>
              <span className="step-num mono">{i + 1}</span>
              <div>
                <h3>{name}</h3>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2>Why "Sleeper"?</h2>
        <p>
          A sleeper is a record that flew under the radar. The scoring leans slightly away from the biggest artists, so the
          pick is more likely to be something you haven't heard yet.
        </p>
      </section>

      <section>
        <h2>How well it works</h2>
        <p>
          Sleeper is tested by hiding one album from a set of six that a real listener likes, giving it the other five, and
          checking whether the hidden one shows up in the top 20. It does 45% of the time, and finds the right artist 78% of
          the time. The full results, including a comparison with a simpler approach, are in the project README.
        </p>
      </section>

      <section>
        <h2>The API</h2>
        <p>
          The engine runs behind a small FastAPI backend, and the website is just one client of it. Every response from
          Last.fm and MusicBrainz is cached in SQLite and rate limited, so repeat requests are instant and the app stays
          within each service's limits.
        </p>
        <pre className="code" aria-label="Example request and response">
          <code>
            <span className="code-method">POST</span> /recommend{'\n'}
            {'{ "album_ids": [ "0da340a0…", "ba660007…", … 5 IDs ] }'}{'\n\n'}
            <span className="code-comment">{'// response'}</span>{'\n'}
            {'{\n  "main": {\n    "title": "PARTYNEXTDOOR",\n    "reason": "shares the rnb and hip hop of your picks; similar to…",\n    "listen_url": "https://www.youtube.com/results?search_query=…"\n  },\n  "runners_up": [ … 4 more ]\n}'}
          </code>
        </pre>
        <ul className="endpoints">
          {ENDPOINTS.map(([method, path, what]) => (
            <li key={path}>
              <span className="mono endpoint-method">{method}</span>
              <span className="mono">{path}</span>
              <span className="muted">{what}</span>
            </li>
          ))}
        </ul>
        <a className="nav-link api-link" href={API_DOCS_URL} target="_blank" rel="noreferrer">
          Try it in the interactive API docs <ArrowUpRight size={16} weight="bold" aria-hidden="true" />
        </a>
      </section>

      <section>
        <h2>Built with</h2>
        <ul className="stack">
          {STACK.map((name) => (
            <li key={name} className="mono">{name}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Data and privacy</h2>
        <p>
          Music data comes from Last.fm and MusicBrainz, and covers from the Cover Art Archive. There are no accounts and
          no personal data is stored. A shared link only contains the IDs of the five albums.
        </p>
      </section>

      <a className="listen-btn" href={REPO_URL} target="_blank" rel="noreferrer">
        Source on GitHub <ArrowUpRight size={16} weight="bold" aria-hidden="true" />
      </a>
    </div>
  )
}
