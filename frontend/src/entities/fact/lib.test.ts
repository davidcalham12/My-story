import { describe, expect, it } from 'vitest'
import { breaksLimits, listChapters, normalise } from './lib'

/**
 * Rule 4: *nothing painful slips through* — and SPEC-EXAM-002 criterion 6,
 * *a correction that would introduce a forbidden word is refused before any
 * chapter is rewritten*.
 *
 * Before, and not after: after is a model paid to write a sentence containing
 * the name of the buyer's dead dog, and a version of the book they then have to
 * be told to ignore.
 *
 * The matching is the backend's, deliberately: `domain.normalise` casefolds and
 * strips the accents NFKD separates, because `Erótico` and `erotico` are the
 * same word to everyone except a string comparison and the buyer types whichever
 * their keyboard offers.
 */

describe('a correction that would break a limit', () => {
  it('finds the forbidden word whatever case it arrives in', () => {
    expect(breaksLimits('The Monster in the cupboard', ['monster'])).toEqual(['monster'])
    expect(breaksLimits('the monster', ['Monster'])).toEqual(['Monster'])
  })

  it('finds it through the accents a keyboard may or may not have put there', () => {
    expect(normalise('Erótico')).toBe('erotico')
    expect(breaksLimits('un cuento erotico', ['erótico'])).toEqual(['erótico'])
  })

  it('matches inside a word, as the backend does', () => {
    // A word survives whatever the buyer wrapped it in. The cost of a false
    // positive is a sentence reworded; the cost of a miss is the thing the
    // buyer asked us never to write.
    expect(breaksLimits('deathly quiet', ['death'])).toEqual(['death'])
  })

  it('names every limit the wording breaks, not just the first', () => {
    expect(breaksLimits('death and monsters', ['death', 'monster'])).toEqual(['death', 'monster'])
  })

  it('finds nothing in a wording that breaks nothing', () => {
    expect(breaksLimits('the dog is called Nala', ['death', 'monster'])).toEqual([])
    expect(breaksLimits('anything at all', [])).toEqual([])
  })

  it('ignores an empty limit rather than matching everything', () => {
    // An empty string is inside every string. A blank row left in the form
    // would otherwise forbid every correction the buyer could possibly type.
    expect(breaksLimits('the dog is called Nala', ['', '  '])).toEqual([])
  })
})

describe('the chapters a fact reaches, in words', () => {
  it('reads one, two and several', () => {
    expect(listChapters([3])).toBe('chapter 3')
    expect(listChapters([3, 5])).toBe('chapters 3 and 5')
    expect(listChapters([3, 5, 7])).toBe('chapters 3, 5 and 7')
  })

  it('says "not recorded" for a fact with no usage rows', () => {
    // `[]` is a fact nothing has been recorded for — not a fact used in chapter
    // zero, and not a fact known to be unused.
    expect(listChapters([])).toBe('not recorded')
  })
})
