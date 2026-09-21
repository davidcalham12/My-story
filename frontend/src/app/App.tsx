import { useState } from 'react'
import { Library } from '@/pages/library/Library'
import { NewNovel } from '@/pages/new-novel/NewNovel'
import { RunPage } from '@/pages/run/RunPage'
import { Boundary } from '@/shared/ui/Boundary'

type Place = { at: 'library' } | { at: 'new' } | { at: 'run'; id: string }

export function App() {
  const [place, setPlace] = useState<Place>({ at: 'library' })
  const home = () => setPlace({ at: 'library' })

  return (
    <main>
      <nav>
        <button
          type="button"
          className={place.at === 'library' ? 'active' : ''}
          onClick={home}
        >
          Library
        </button>
        <button
          type="button"
          className={place.at === 'new' ? 'active' : ''}
          onClick={() => setPlace({ at: 'new' })}
        >
          New novel
        </button>
      </nav>

      {/* Keyed, because a boundary that has caught stays caught: without the key,
          opening a different run would show the previous one's error. */}
      <Boundary what="This screen" key={JSON.stringify(place)} onEscape={home}>
        {place.at === 'library' && (
          <Library
            onOpen={(id) => setPlace({ at: 'run', id })}
            onNew={() => setPlace({ at: 'new' })}
          />
        )}
        {place.at === 'new' && (
          <NewNovel onStarted={(id) => setPlace({ at: 'run', id })} />
        )}
        {place.at === 'run' && <RunPage runId={place.id} />}
      </Boundary>
    </main>
  )
}
