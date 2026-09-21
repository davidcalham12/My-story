import { useState } from 'react'
import { api } from '@/shared/api/client'

const PROFILES = [
  ['tiny', '3 chapters — the whole pipeline in minutes'],
  ['small', '8 chapters — a long short story'],
  ['medium', '18 chapters — a short novel'],
  ['full', '34 chapters'],
]

const EXAMPLES = [
  'A deep-space salvage crew finds a derelict that remembers them',
  'Michael Jackson spends an afternoon learning to make quesadillas',
  'A retired detective takes one last case: who keeps moving her neighbour’s bins',
]

/** Starting a run. The genre is read off the premise unless one is given. */
export function NewNovel({ onStarted }: { onStarted: (id: string) => void }) {
  const [premise, setPremise] = useState('')
  const [profile, setProfile] = useState('tiny')
  const [tone, setTone] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const start = async () => {
    setBusy(true)
    setError(null)
    try {
      const { id } = await api.start(premise.trim(), profile, tone.trim())
      onStarted(id)
    } catch (e) {
      setError(String(e))
      setBusy(false)
    }
  }

  return (
    <>
      <h1>A new novel</h1>

      <div className="field">
        <label htmlFor="premise">What should it be about?</label>
        <textarea
          id="premise"
          rows={3}
          value={premise}
          placeholder="One or two sentences."
          onChange={(e) => setPremise(e.target.value)}
        />
        <div className="hint">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" onClick={() => setPremise(example)}>
              {example}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label htmlFor="tone">What kind of book is it?</label>
        <input
          id="tone"
          type="text"
          value={tone}
          placeholder="Leave empty and the genre is read off the premise"
          onChange={(e) => setTone(e.target.value)}
        />
        <p className="hint">
          No agent declares a genre. In v1 all nine did, and a premise about a pop
          star trying quesadillas came back with factions and a bandwidth budget.
          Whatever is decided here is recorded in the run&rsquo;s config snapshot.
        </p>
      </div>

      <div className="field">
        <label htmlFor="profile">How long?</label>
        <select id="profile" value={profile} onChange={(e) => setProfile(e.target.value)}>
          {PROFILES.map(([name, blurb]) => (
            <option key={name} value={name}>
              {name} — {blurb}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="panel panel--bad">{error}</p>}

      <button
        type="button"
        className="primary"
        disabled={busy || premise.trim().length < 10}
        onClick={start}
      >
        {busy ? 'Starting…' : 'Write it'}
      </button>
    </>
  )
}
