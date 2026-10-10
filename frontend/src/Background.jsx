import { useEffect, useMemo, useState } from 'react'

// Decorative page background: a grid of colored boxes that light up and fade
// at random, like an LED wall, plus a big vinyl record slowly spinning in the
// corner. aria-hidden because it's purely visual.
const TILE = 54 // px per box, including the gap
// Repeats make a color more likely: mostly blues, and only about 1 box in 9
// is a warm yellow "lit window".
const COLORS = [
  'var(--led-1)', 'var(--led-1)', 'var(--led-1)',
  'var(--led-2)', 'var(--led-2)', 'var(--led-2)',
  'var(--led-3)', 'var(--led-3)',
  'var(--led-4)',
]
const GROOVES = [90, 82, 74, 66, 58, 50, 42]

// How many boxes it takes to cover the window (one extra row/column so the
// edges never show a gap).
function gridSize() {
  return {
    cols: Math.ceil(window.innerWidth / TILE) + 1,
    rows: Math.ceil(window.innerHeight / TILE) + 1,
  }
}

export default function Background() {
  const [size, setSize] = useState(gridSize)

  useEffect(() => {
    const onResize = () => setSize(gridSize())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Give every box a random color, speed and starting point once, and only
  // redo it when the grid size changes, so boxes don't reshuffle on every
  // render. The negative delay starts each box partway through its cycle, so
  // the wall is already twinkling on page load instead of all flashing at once.
  const tiles = useMemo(
    () =>
      Array.from({ length: size.cols * size.rows }, () => ({
        background: COLORS[Math.floor(Math.random() * COLORS.length)],
        animationDuration: `${12 + Math.random() * 14}s`,
        animationDelay: `${-Math.random() * 26}s`,
      })),
    [size.cols, size.rows],
  )

  return (
    <div className="bg" aria-hidden="true">
      <div className="leds" style={{ gridTemplateColumns: `repeat(${size.cols}, ${TILE}px)` }}>
        {tiles.map((style, i) => (
          <div key={i} className="led" style={style} />
        ))}
      </div>
      <svg className="vinyl" viewBox="0 0 200 200">
        <circle className="vinyl-disc" cx="100" cy="100" r="98" />
        {GROOVES.map((r) => (
          <circle key={r} className="vinyl-groove" cx="100" cy="100" r={r} />
        ))}
        {/* A circle spinning looks identical at every angle, so this light
            wedge and the off-center dot on the label are what make the
            rotation visible. */}
        <path className="vinyl-shine" d="M100 100 L100 2 A98 98 0 0 1 169 31 Z" />
        <circle className="vinyl-label" cx="100" cy="100" r="30" />
        <circle className="vinyl-hole" cx="112" cy="88" r="3" />
        <circle className="vinyl-hole" cx="100" cy="100" r="3" />
      </svg>
    </div>
  )
}
