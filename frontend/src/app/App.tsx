import { useState } from 'react'
import { AskForAChange } from '@/pages/ask-for-a-change/AskForAChange'
import { Interview } from '@/pages/interview/Interview'
import { Library } from '@/pages/library/Library'
import { NewNovel } from '@/pages/new-novel/NewNovel'
import { Read } from '@/pages/read/Read'
import { RunPage } from '@/pages/run/RunPage'
import { Boundary } from '@/shared/ui/Boundary'

type Place =
  | { at: 'library' }
  | { at: 'interview' }
  | { at: 'quick' }
  | { at: 'run'; id: string }
  | { at: 'read'; id: string }
  | { at: 'change'; id: string }

/** The three screens a novel has once it exists. Shown only when one is open,
 *  because a reader with no book has nothing to read and nothing to correct. */
const OF_A_NOVEL = [
  ['run', 'Writing'],
  ['read', 'Read'],
  ['change', 'Ask for a change'],
] as const

export function App() {
  const [place, setPlace] = useState<Place>({ at: 'library' })
  const home = () => setPlace({ at: 'library' })
  const openRun = 'id' in place ? place.id : null

  return (
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <button type="button" className="link brand" onClick={home} aria-label="storyMaker, go to the library">
            <span className="brand__name">storyMaker<span className="brand__dot">.</span></span>
            <span className="brand__by">by Qaracter</span>
          </button>
          <nav aria-label="Sections" className="topnav">
            <button
              type="button"
              className={place.at === 'library' ? 'active' : ''}
              onClick={home}
            >
              Library
            </button>
            <button
              type="button"
              className={place.at === 'interview' ? 'active' : ''}
              onClick={() => setPlace({ at: 'interview' })}
            >
              New novel
            </button>
            {/* The premise-only path that predates the interview. Kept because it
                is how a short test run is started without answering nine
                questions about an imaginary child. */}
            <button
              type="button"
              className={place.at === 'quick' ? 'active' : ''}
              onClick={() => setPlace({ at: 'quick' })}
            >
              Quick run
            </button>
          </nav>
        </div>
      </header>

    <main>
      {openRun && (
        <nav aria-label="This novel" className="tabs">
          {OF_A_NOVEL.map(([at, label]) => (
            <button
              key={at}
              type="button"
              className={place.at === at ? 'active' : ''}
              aria-current={place.at === at ? 'page' : undefined}
              onClick={() => setPlace({ at, id: openRun })}
            >
              {label}
            </button>
          ))}
        </nav>
      )}

      {/* Keyed, because a boundary that has caught stays caught: without the key,
          opening a different run would show the previous one's error. */}
      <Boundary what="This screen" key={JSON.stringify(place)} onEscape={home}>
        {place.at === 'library' && (
          <Library
            onOpen={(id) => setPlace({ at: 'run', id })}
            onNew={() => setPlace({ at: 'interview' })}
          />
        )}
        {place.at === 'interview' && (
          <Interview onStarted={(id) => setPlace({ at: 'run', id })} />
        )}
        {place.at === 'quick' && (
          <NewNovel onStarted={(id) => setPlace({ at: 'run', id })} />
        )}
        {place.at === 'run' && <RunPage runId={place.id} />}
        {place.at === 'read' && (
          <Read runId={place.id} onAskForAChange={() => setPlace({ at: 'change', id: place.id })} />
        )}
        {place.at === 'change' && (
          <AskForAChange
            runId={place.id}
            onVersion={() => setPlace({ at: 'read', id: place.id })}
          />
        )}
      </Boundary>
    </main>
    </>
  )
}
