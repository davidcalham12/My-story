/**
 * The facts a novel rests on, and the limits a correction may not break.
 *
 * `normalise` is `backend/brief/domain.normalise` in TypeScript: casefold, then
 * drop the marks NFKD separates. Eleven lines by hand rather than a dependency —
 * `String.prototype.normalize` is in the language, and the combining-mark range
 * is one regular expression. A package for this would be a package to audit,
 * update and explain for the sake of a line of code.
 *
 * The rule it serves is rule 4: *nothing painful slips through*. A correction
 * that would introduce a word the buyer asked us never to use is refused
 * **before** anything is spent — after is a model paid to write the name of
 * their dead dog into a chapter.
 */

export function normalise(text: string): string {
  // NFKD splits "ó" into "o" + a combining acute; ̀-ͯ is that block.
  return text.normalize('NFKD').toLowerCase().replace(/[̀-ͯ]/g, '')
}

/** Every limit the wording breaks, in the order the buyer wrote them. */
export function breaksLimits(wording: string, forbidden: string[]): string[] {
  const hay = normalise(wording)
  // A blank row left in the form is not a limit: the empty string is inside
  // every string, and it would forbid every correction the buyer could type.
  return forbidden.filter((term) => term.trim() !== '' && hay.includes(normalise(term.trim())))
}

/**
 * The chapters a fact reaches, as a sentence.
 *
 * `[]` is a fact nothing has been recorded for — not a fact used in chapter
 * zero, and not a fact known to be unused. Those are three different claims and
 * only one of them is true here.
 */
export function listChapters(chapters: number[]): string {
  const sorted = [...chapters].sort((a, b) => a - b)
  if (sorted.length === 0) return 'not recorded'
  if (sorted.length === 1) return `chapter ${sorted[0]}`
  const last = sorted[sorted.length - 1]
  return `chapters ${sorted.slice(0, -1).join(', ')} and ${last}`
}
