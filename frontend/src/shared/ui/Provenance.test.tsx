import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Provenance } from './Provenance'
import { MARK, MEANING } from '@/shared/lib/provenance'
import type { Provenance as Grade } from '@/shared/api/types'

/**
 * G12's other half: the grade has to reach the screen.
 *
 * The database has refused a figure without a provenance grade since the first
 * migration, and `verification.md` carried that row as **T (partial)** because
 * nothing checked the render. A grade stored and not shown is a grade nobody
 * acts on, which is the same outcome as not having one.
 *
 * Rendered to a string rather than into a DOM on purpose: it needs no jsdom and
 * no testing-library, so the assertion costs a dependency of zero and runs in
 * CI at $0 like everything else here.
 */

const GRADES: Grade[] = ['measured', 'reported', 'reconstructed', 'estimated', 'absent']

describe('a figure never appears without saying where it came from', () => {
  it('renders a mark for every grade, and they are distinguishable', () => {
    const marks = GRADES.map((g) => MARK[g])
    expect(new Set(marks).size).toBe(GRADES.length)
    for (const grade of GRADES) {
      expect(renderToStaticMarkup(<Provenance grade={grade} />)).toContain(MARK[grade])
    }
  })

  it('names the grade in the title, so the mark is readable by someone who has not read the docs', () => {
    for (const grade of GRADES) {
      const html = renderToStaticMarkup(<Provenance grade={grade} />)
      expect(html).toContain(grade)
      expect(html).toContain(MEANING[grade])
    }
  })

  it('says absent means "not the same as zero"', () => {
    // The rule the whole grade system exists for. A run that destroyed its
    // evidence and a run where nothing happened are identical in a number.
    expect(renderToStaticMarkup(<Provenance grade="absent" />)).toContain('not the same as zero')
  })

  it('carries the grade in a class, so absent is visually distinct rather than quiet', () => {
    expect(renderToStaticMarkup(<Provenance grade="absent" />)).toContain('prov--absent')
    expect(renderToStaticMarkup(<Provenance grade="measured" />)).toContain('prov--measured')
  })
})
