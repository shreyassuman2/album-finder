import { useEffect } from 'react'
import { ArrowLeft, ArrowUpRight } from '@phosphor-icons/react'

const REPO_URL = 'https://github.com/shreyassuman2/sleeper'

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
        <h2>Data and privacy</h2>
        <p>
          Music data comes from Last.fm and MusicBrainz, and covers from the Cover Art Archive. There are no accounts and
          no personal data is stored. The site counts anonymous page views with Vercel Analytics (no cookies). A shared
          link only contains the IDs of the five albums.
        </p>
      </section>

      <a className="listen-btn" href={REPO_URL} target="_blank" rel="noreferrer">
        Source on GitHub <ArrowUpRight size={16} weight="bold" aria-hidden="true" />
      </a>
    </div>
  )
}
