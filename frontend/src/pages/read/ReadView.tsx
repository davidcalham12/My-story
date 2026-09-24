import type {
  ChapterEntry, CharacterEntry, PlaceEntry, VersionRow,
} from '@/shared/api/types'
import type { Changed } from '@/entities/version/lib'
import { pdfUrl } from '@/shared/api/client'

/**
 * The novel, as a book, with its apparatus beside it.
 *
 * Everything is a prop: the test renders this to a string and asserts on the
 * HTML, with no DOM and no stubbed `fetch`. `Read.tsx` fetches.
 *
 * The PDF is shown by the browser's own viewer in an `<object>`. That is the
 * whole reason this screen needs no PDF library — the exam's zero-dependency
 * rule and the reader's experience agree here, because the browser's viewer
 * already knows how to print, search and zoom.
 */

interface Props {
  runId: string
  versions: VersionRow[]
  /** null while nothing has been published. Never 0: zero is not a version. */
  chosen: number | null
  chapters: ChapterEntry[]
  characters: CharacterEntry[]
  places: PlaceEntry[]
  /** What this version rewrote, or the fact that nobody recorded it. */
  changed: Changed | null
  error: string | null
  onChoose: (n: number) => void
  onAskForAChange: () => void
}

/** A link to a chapter, or the words for not having one.
 *
 *  `first_chapter` of null is an entry nobody recorded a first appearance for.
 *  `#chapter-0` would be a link to a place in the book that does not exist. */
function Appears({ chapter }: { chapter: number | null }) {
  if (chapter === null) return <span className="muted">chapter not recorded</span>
  return <a href={`#chapter-${chapter}`}>chapter {chapter}</a>
}

export function ReadView(props: Props) {
  const { runId, versions, chosen, chapters, characters, places, changed, error } = props
  const open = versions.find((v) => v.n === chosen) ?? null

  return (
    <div className="reader">
      <div>
        <section className="hero">
          <p className="eyebrow eyebrow--brand">Read</p>
          <h1>{versions.length > 0 ? 'Your book, ready to read' : 'The book is not published yet'}</h1>
          <p className="lede">
            {versions.length > 0
              ? 'Choose a version, read it here or download the PDF. Every earlier version stays available.'
              : 'It appears here as soon as the last chapter passes its checks.'}
          </p>
        </section>

        {error && <p className="panel panel--bad">{error}</p>}

        {versions.length > 0 && (
          <nav aria-label="Versions">
            {[...versions]
              .sort((a, b) => a.n - b.n)
              .map((v) => (
                <button
                  key={v.n}
                  type="button"
                  aria-pressed={v.n === chosen}
                  className={v.n === chosen ? 'active' : undefined}
                  onClick={() => props.onChoose(v.n)}
                >
                  Version {v.n}
                  {v.n === 1 ? '' : ' — after your change'}
                </button>
              ))}
          </nav>
        )}

        {changed && chosen !== null && chosen > 1 && (
          <div className="panel panel--note">
            <h2>What changed in this version</h2>
            {changed.recorded ? (
              <p>
                {changed.chapters.map((n, i) => (
                  <span key={n}>
                    {i > 0 && ', '}
                    <a href={`#chapter-${n}`}>chapter {n}</a>
                  </span>
                ))}{' '}
                {changed.chapters.length === 1 ? 'was rewritten' : 'were rewritten'} after your
                change. Every other chapter is word for word what it was, and version{' '}
                {(chosen ?? 2) - 1} is still one click away above.
              </p>
            ) : (
              // The archive keeps a reason, not a chapter list. Saying "none"
              // would be a lie in the reader's favour: a regeneration that
              // touches no chapter is refused before it starts.
              <p>
                This version was made after a change you asked for, but which chapters it
                rewrote was <strong>not recorded</strong>. The earlier version is still
                above, unchanged.
              </p>
            )}
          </div>
        )}

        {versions.length === 0 && (
          <p className="panel">
            This novel is <strong>still being written</strong>. The book appears here as soon
            as the first version is published; nothing is lost if you close the page.
          </p>
        )}

        {open && !open.pdf && (
          <p className="panel panel--halt">
            Version {open.n} was published, but its PDF <strong>was not printed</strong>.
            Printing needs a browser of its own and can fail where the writing did not, so
            there is nothing to show here yet — which is not the same as the version being
            empty.
          </p>
        )}

        {open && open.pdf && chosen !== null && (
          <object
            className="reader__viewer"
            data={pdfUrl(runId, chosen)}
            type="application/pdf"
            aria-label={`The novel, version ${chosen}`}
          >
            <p>
              Your browser will not show the book inline.{' '}
              <a href={pdfUrl(runId, chosen)}>Open version {chosen} as a PDF</a>.
            </p>
          </object>
        )}
      </div>

      <aside>
        <h2>Chapters</h2>
        {chapters.length === 0 ? (
          <p className="muted">No chapter list was recorded for this version.</p>
        ) : (
          <ol className="list">
            {chapters.map((c) => (
              <li key={c.n}>
                <a href={`#chapter-${c.n}`}>
                  {c.n}. {c.title}
                </a>
              </li>
            ))}
          </ol>
        )}

        <h2>Who and where</h2>
        {characters.length === 0 && places.length === 0 ? (
          <p className="muted">No character or place sheet was recorded for this novel.</p>
        ) : (
          <ul className="list">
            {characters.map((c) => (
              <li key={`c-${c.canonical_name}`}>
                <strong>{c.canonical_name}</strong>
                {c.role ? ` — ${c.role}` : ''} · <Appears chapter={c.first_chapter} />
              </li>
            ))}
            {places.map((p) => (
              <li key={`p-${p.canonical_name}`}>
                <strong>{p.canonical_name}</strong>
                {p.note ? ` — ${p.note}` : ''} · <Appears chapter={p.first_chapter} />
              </li>
            ))}
          </ul>
        )}

        <p>
          <button type="button" onClick={props.onAskForAChange}>
            Ask for a change
          </button>
        </p>
      </aside>
    </div>
  )
}
