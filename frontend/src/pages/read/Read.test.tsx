import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { ReadView } from './ReadView'
import type {
  ChapterEntry, CharacterEntry, Impact, PlaceEntry, VersionRow,
} from '@/shared/api/types'

/**
 * AC-4, and rule 5: *the old version is sacred*.
 *
 * Rendered to a string, with everything the screen shows handed in as a prop.
 * The PDF is the browser's own viewer and there is nothing to assert inside it,
 * so what is held here is the part that is ours: the picker, the index, the
 * character sheet, and the band that says what a new version changed.
 */

const version = (over: Partial<VersionRow>): VersionRow => ({
  n: 1, parent: null, reason: 'first publication', created_at: '2026-09-23T10:00:00', pdf: true,
  ...over,
})

const CHAPTERS: ChapterEntry[] = [
  { n: 1, title: 'The fossil on the beach' },
  { n: 2, title: 'What is on the other side of the hill' },
]

const CHARACTERS: CharacterEntry[] = [
  { canonical_name: 'Leo', role: 'protagonist', birth_date: null, first_chapter: 1 },
  { canonical_name: 'Bruno', role: 'the dog', birth_date: null, first_chapter: 2 },
  { canonical_name: 'The lighthouse keeper', role: null, birth_date: null, first_chapter: null },
]

const PLACES: PlaceEntry[] = [
  { canonical_name: 'Cadaqués', note: 'the beach', first_chapter: 1 },
  { canonical_name: 'The garden', note: null, first_chapter: null },
]

const render = (over: Partial<Parameters<typeof ReadView>[0]> = {}) =>
  renderToStaticMarkup(
    <ReadView
      runId="r1"
      versions={[version({ n: 1 })]}
      chosen={1}
      chapters={CHAPTERS}
      characters={CHARACTERS}
      places={PLACES}
      changed={null}
      error={null}
      onChoose={() => {}}
      onAskForAChange={() => {}}
      {...over}
    />,
  )

describe('AC-4: the book, as a book', () => {
  it('shows the chosen version in the browser’s own viewer', () => {
    // No PDF library: `<object>` is the browser's viewer, and the URL is by run
    // and version because no route takes a filesystem path.
    expect(render()).toContain('/api/runs/r1/versions/1/pdf')
  })

  it('offers every published version, and says which one is open', () => {
    const html = render({
      versions: [version({ n: 1 }), version({ n: 2, parent: 1, reason: 'reader change to fact 7' })],
      chosen: 2,
    })
    expect(html).toContain('Version 1')
    expect(html).toContain('Version 2')
    // The old one is still reachable. Rule 5: no action deletes a version the
    // buyer has already received.
    expect(html.match(/aria-pressed="true"/g)?.length).toBe(1)
  })

  it('links every chapter of the index to its anchor', () => {
    const html = render()
    expect(html).toContain('href="#chapter-1"')
    expect(html).toContain('href="#chapter-2"')
    expect(html).toContain('The fossil on the beach')
  })

  it('links every character and place to the chapter it first appears in', () => {
    const html = render()
    const leo = html.slice(html.indexOf('Leo'))
    expect(leo).toContain('#chapter-1')
    expect(html).toContain('Cadaqués')
    expect(html).toContain('Bruno')
  })

  it('says "not recorded" for an entry with no chapter, and links nowhere', () => {
    // Absent is a word. `first_chapter` of null is a character nobody recorded
    // a first appearance for — not a character who appears in chapter zero,
    // and `#chapter-0` is a link to a place in the book that does not exist.
    const html = render()
    expect(html).toContain('not recorded')
    expect(html).not.toContain('#chapter-0')
  })
})

describe('AC-5, second half: a new version says what changed', () => {
  const v2 = version({ n: 2, parent: 1, reason: 'reader change to fact 7' })
  const impact: Impact = {
    fact_id: 7, text: 'the dog is called Nala', kind: 'mandatory', source: 'brief',
    mandatory: true, version: 1, chapters: [2], exact: false, matching: 'words',
  }

  it('names the chapters this version rewrote, with a link to each', () => {
    const html = render({
      versions: [version({ n: 1 }), v2], chosen: 2,
      changed: { chapters: [2], recorded: true },
    })
    expect(html).toContain('chapter 2')
    expect(html).toContain('href="#chapter-2"')
    expect(impact.chapters).toEqual([2]) // the shape the banner is fed
  })

  it('says so when nobody recorded which chapters changed', () => {
    // `versions` stores a reason, not a chapter list. "None changed" would be a
    // lie: a regeneration that touches no chapter is refused before it starts.
    const html = render({
      versions: [version({ n: 1 }), v2], chosen: 2,
      changed: { chapters: [], recorded: false },
    })
    expect(html).toContain('not recorded')
    expect(html).not.toContain('no chapters changed')
  })

  it('says nothing of the kind on the first version', () => {
    expect(render()).not.toContain('was rewritten in this version')
  })
})

describe('the states this screen has to have', () => {
  it('says the book is still being written when no version exists', () => {
    const html = render({ versions: [], chosen: null })
    expect(html).toContain('still being written')
    expect(html).not.toContain('<object')
  })

  it('says a version was published without a printed PDF rather than showing a blank', () => {
    // The print needs a browser and can fail where the publish did not. An
    // empty viewer is a 404 the reader gets to discover.
    const html = render({ versions: [version({ n: 1, pdf: false })], chosen: 1 })
    expect(html).toContain('was not printed')
    expect(html).not.toContain('<object')
  })
})
