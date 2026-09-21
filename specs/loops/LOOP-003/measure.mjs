#!/usr/bin/env node
/**
 * LOOP-003 §6 — the instrument.
 *
 * Reads a run's critiques and log and reports, per chapter: the five scores at
 * each attempt, which attempt it passed on, which findings were resolved,
 * carried, newly raised or raised late, how many lines the writer touched
 * against how many the sheet cited, and what the attempt cost.
 *
 * **The writer never measures itself and neither do the critics.** That is the
 * whole reason this file exists rather than a paragraph in SKILL.md asking the
 * orchestrator to keep count. A model asked whether it improved will say yes.
 *
 * Two commands:
 *
 *   node measure.mjs <slug>        report on one run
 *   node measure.mjs --self-test   §6.2, against the committed run
 *
 * §6.2 fixes what the self-test must reproduce, and it is deliberately a run
 * that already exists: an instrument that cannot recover a known history is an
 * instrument, not a measurement.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO = path.resolve(HERE, '..', '..', '..')
const OUTPUT = path.join(REPO, 'output')

/** The five characteristics of §1, in the order the sheet prints them. */
export const FEATURES = ['continuity', 'science', 'outline', 'length', 'chatter']
export const THRESHOLD = 8
export const MAX_ATTEMPTS = 3

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'))
const exists = (p) => fs.existsSync(p)
const pad = (n) => String(n).padStart(2, '0')

/**
 * A finding's identity is its quote.
 *
 * Nothing else survives a redraft: severity gets revised, the wording of the
 * fix changes, and the critic does not number them. The quote is the one field
 * that is copied from the draft character for character, which is what makes
 * "the same finding" a question with an answer rather than a judgement.
 */
const idOf = (finding) => (finding.quote ?? finding.claim ?? finding.problem ?? '').trim()

/** Critique files in three shapes; see web/src/data/load.ts for why. */
function iterationsOf(file) {
  if (Array.isArray(file)) return file
  if (Array.isArray(file?.iterations)) return file.iterations
  if (typeof file?.score === 'number') return [{ iteration: 1, ...file }]
  return []
}

export function readRun(slug) {
  const dir = path.join(OUTPUT, slug)
  if (!exists(dir)) throw new Error(`no such run: ${slug}`)

  const logFile = path.join(dir, 'logs', 'agents.jsonl')
  const log = exists(logFile)
    ? fs
        .readFileSync(logFile, 'utf8')
        .trim()
        .split('\n')
        .filter(Boolean)
        .flatMap((line) => {
          try {
            return [JSON.parse(line)]
          } catch {
            return []
          }
        })
    : []

  const state = exists(path.join(dir, 'state.json')) ? readJson(path.join(dir, 'state.json')) : null
  const chapters = state?.chapters?.length ?? 0

  return { dir, log, state, chapters }
}

/**
 * Everything §6.1 asks for, for one chapter.
 *
 * A field this cannot obtain is `null`, never zero. `linesTouched` is the one
 * that is usually null: it needs the rejected drafts, and a run that keeps only
 * the accepted one has thrown away the evidence. G3 is unmeasurable there, and
 * saying so is the measurement.
 */
export function measureChapter(run, n) {
  const perFeature = {}
  for (const feature of FEATURES) {
    const file = path.join(run.dir, 'critiques', `ch${pad(n)}.${feature}.json`)
    perFeature[feature] = exists(file) ? iterationsOf(readJson(file)) : []
  }

  const attemptNumbers = [
    ...new Set(Object.values(perFeature).flatMap((its) => its.map((it) => it.iteration ?? 1))),
  ].sort((a, b) => a - b)

  const attempts = attemptNumbers.map((k) => {
    const scores = {}
    const findings = []
    for (const feature of FEATURES) {
      const it = perFeature[feature].find((i) => (i.iteration ?? 1) === k)
      if (!it) continue
      if (typeof it.score === 'number') scores[feature] = it.score
      for (const f of it.findings ?? []) findings.push({ ...f, feature })
    }

    const scored = Object.values(scores)
    const upheld = findings.filter((f) => f.upheld !== false)

    return {
      attempt: k,
      scores,
      // A feature with no usable verdict is excluded, not counted as a pass —
      // the same rule the gate itself runs on.
      missing: FEATURES.filter((f) => !(f in scores)),
      lowest: scored.length ? Math.min(...scored) : null,
      passed: scored.length === FEATURES.length && scored.every((s) => s >= THRESHOLD),
      findings,
      upheldCount: upheld.length,
      overruledCount: findings.length - upheld.length,
      linesTouched: linesTouched(run, n, k),
      linesCited: upheld.reduce((sum, f) => sum + quoteLines(f), 0),
      sheet: sheetFor(run, n, k),
      tokens: tokensFor(run, n, k),
    }
  })

  /**
   * What the sheet that commissioned THIS attempt actually cited.
   *
   * G3 is "lines changed <= lines quoted x 2", and the quoted lines are the
   * ones in the sheet the writer was handed — which belong to the previous
   * attempt's findings, not to this one's. The first version of this file
   * compared attempt k's diff against attempt k's own citations, so a final
   * attempt that passed clean cited nothing and any repair at all failed the
   * test against zero. It reported 2/7 on a run that is 7/7.
   *
   * The run found this, not the author: the orchestrator reported the artifact
   * rather than the number, which is the behaviour the instrument exists to
   * make possible. `linesCited` stays as the citations raised AGAINST a draft,
   * because that is what it means; `citedToMe` is the pair G3 wants.
   */
  for (let i = 0; i < attempts.length; i += 1) {
    attempts[i].citedToMe = i === 0 ? null : attempts[i - 1].linesCited
  }

  // Resolved / carried / late, by comparing quotes between attempts.
  for (let i = 1; i < attempts.length; i += 1) {
    const before = new Set(attempts[i - 1].findings.filter((f) => f.upheld !== false).map(idOf))
    const now = new Set(attempts[i].findings.map(idOf))
    attempts[i].resolved = [...before].filter((q) => !now.has(q)).length
    attempts[i].carried = [...before].filter((q) => now.has(q)).length
    attempts[i].fresh = [...now].filter((q) => !before.has(q)).length
  }
  if (attempts[0]) {
    attempts[0].resolved = 0
    attempts[0].carried = 0
    attempts[0].fresh = attempts[0].findings.length
  }

  // §3.1 — a finding raised late whose quote was present in the first draft
  // and went unmentioned is the goalposts moving. It is recorded, patched where
  // possible, and does not block.
  const firstDraft = draftText(run, n, 1)
  for (const a of attempts) {
    if (a.attempt === 1) {
      a.late = 0
      continue
    }
    a.late = firstDraft
      ? a.findings.filter((f) => {
          const q = idOf(f)
          const seenBefore = attempts
            .filter((x) => x.attempt < a.attempt)
            .some((x) => x.findings.some((g) => idOf(g) === q))
          return !seenBefore && q.length > 12 && firstDraft.includes(q)
        }).length
      : null
  }

  const passing = attempts.find((a) => a.passed)
  return {
    chapter: n,
    attempts,
    unattributedTokens: unattributedTokens(run, n),
    passedAt: passing?.attempt ?? null,
    neededPatch: !passing && attempts.length >= MAX_ATTEMPTS,
  }
}

/** The text of one attempt's draft, when the run kept it. */
function draftText(run, n, k) {
  for (const name of [`ch${pad(n)}.attempt${k}.md`, k === 1 ? `ch${pad(n)}.md` : null]) {
    if (!name) continue
    const p = path.join(run.dir, 'chapters', name)
    if (exists(p)) return fs.readFileSync(p, 'utf8')
  }
  return null
}

/**
 * Lines the writer changed between attempt k-1 and k.
 *
 * `null` when the run did not keep the earlier draft, which is not the same as
 * zero and must never be reported as it: a run that overwrites its rejected
 * drafts has destroyed the only evidence G3 is measurable from.
 */
function linesTouched(run, n, k) {
  if (k < 2) return null
  const before = draftText(run, n, k - 1)
  const after = draftText(run, n, k)
  if (before === null || after === null) return null

  const a = before.split(/\r?\n/)
  const b = after.split(/\r?\n/)
  const inB = new Set(b.map((l) => l.trim()).filter(Boolean))
  const inA = new Set(a.map((l) => l.trim()).filter(Boolean))
  const gone = [...inA].filter((l) => !inB.has(l)).length
  const added = [...inB].filter((l) => !inA.has(l)).length
  return Math.max(gone, added)
}

/** A quote spans this many lines of the draft it was copied from. */
const quoteLines = (f) => ((f.quote ?? '').match(/\n/g)?.length ?? 0) + 1

/**
 * The sheet sent for this attempt, when one was recorded.
 *
 * Under the run's own slug, because `sheets/chNN.attemptK.md` has no run
 * dimension and the second run to use this loop silently overwrote the first's
 * chapter 1 and chapter 3 sheets. They were recoverable from git and were
 * restored byte-exact, which is luck rather than design: the sheets are the
 * only record of what the writer was actually told, and §8.1 says the thing
 * this loop learns is read out of them. The flat path is still read as a
 * fallback so sheets written before this are not lost.
 */
function sheetFor(run, n, k) {
  const slug = path.basename(run.dir)
  for (const p of [
    path.join(HERE, 'sheets', slug, `ch${pad(n)}.attempt${k}.md`),
    path.join(HERE, 'sheets', `ch${pad(n)}.attempt${k}.md`),
  ]) {
    if (exists(p)) return { path: p, text: fs.readFileSync(p, 'utf8') }
  }
  return null
}

/**
 * Tokens attributable to one attempt.
 *
 * A row with no `iteration` used to land in attempt 1, because `?? 1` treats
 * "not stated" as "the first". Arbitration calls are logged that way, so one
 * chapter's attempt 1 read 91,489 tokens — a number large enough to be believed
 * and wrong. Only a stated iteration counts here; what is left over is reported
 * against the chapter by `unattributedTokens`, because those tokens were spent
 * and belong somewhere visible rather than in whichever bucket a default picks.
 */
function tokensFor(run, n, k) {
  const rows = run.log.filter(
    (r) => r.agent && r.chapter === n && r.iteration === k && typeof r.tokens === 'number',
  )
  return rows.length ? rows.reduce((t, r) => t + r.tokens, 0) : null
}

/** Tokens logged against a chapter with no attempt named. */
function unattributedTokens(run, n) {
  const rows = run.log.filter(
    (r) =>
      r.agent &&
      r.chapter === n &&
      typeof r.iteration !== 'number' &&
      typeof r.tokens === 'number',
  )
  return rows.length ? rows.reduce((t, r) => t + r.tokens, 0) : 0
}

// ---------------------------------------------------------------- reporting

export function measureRun(slug) {
  const run = readRun(slug)
  const chapters = []
  for (let n = 1; n <= run.chapters; n += 1) chapters.push(measureChapter(run, n))
  return { slug, chapters }
}

function report(slug) {
  const { chapters } = measureRun(slug)
  console.log(`LOOP-003 — ${slug}\n`)
  for (const ch of chapters) {
    const where = ch.passedAt ? `passed at attempt ${ch.passedAt}` : 'never passed'
    console.log(
      `chapter ${ch.chapter} — ${where}` +
        (ch.unattributedTokens
          ? ` · ${ch.unattributedTokens.toLocaleString('en-GB')} tokens logged with no attempt named`
          : ''),
    )
    for (const a of ch.attempts) {
      const scores = FEATURES.map((f) => `${f} ${a.scores[f] ?? '—'}`).join(' · ')
      console.log(`  attempt ${a.attempt}: ${scores}`)
      console.log(
        `    lowest ${a.lowest ?? '—'} · findings ${a.findings.length}` +
          ` (${a.overruledCount} overruled) · resolved ${a.resolved} · carried ${a.carried}` +
          ` · new ${a.fresh} · late ${a.late ?? 'not measurable'}`,
      )
      console.log(
        `    lines touched ${a.linesTouched ?? 'not measurable (no kept draft)'}` +
          ` · raised against it ${a.linesCited}` +
          ` · its sheet cited ${a.citedToMe ?? '—'}` +
          ` · tokens ${a.tokens ?? '—'}` +
          ` · sheet ${a.sheet ? 'recorded' : 'not recorded'}`,
      )
      if (a.missing.length) console.log(`    UNSCORED: ${a.missing.join(', ')}`)
    }
  }

  // §5 — the four goals, as far as this run can answer them.
  const done = chapters.filter((c) => c.passedAt)
  console.log('\nagainst the goals:')
  console.log(
    `  G1 valid by the third attempt: ${done.length}/${chapters.length}` +
      `${chapters.some((c) => c.neededPatch) ? ' (some needed the patch)' : ''}`,
  )
  const early = done.filter((c) => c.passedAt <= 2).length
  console.log(`  G2 passed on the 1st or 2nd: ${early}/${chapters.length}`)
  const measurable = chapters.flatMap((c) =>
    c.attempts.filter((a) => a.linesTouched !== null && a.citedToMe !== null),
  )
  console.log(
    measurable.length
      ? `  G3 touched vs cited: ${measurable.filter((a) => a.linesTouched <= a.citedToMe * 2).length}/${measurable.length} within 2x` +
          ` (touched at attempt k against what the sheet for k cited, which is k-1's findings)`
      : '  G3 NOT MEASURABLE — this run kept no rejected drafts, so no diff exists',
  )
  const lateKnown = chapters.flatMap((c) => c.attempts.filter((a) => a.late !== null))
  const lateTotal = lateKnown.reduce((t, a) => t + a.late, 0)
  const findingTotal = chapters.flatMap((c) => c.attempts).reduce((t, a) => t + a.findings.length, 0)
  console.log(
    lateKnown.length
      ? `  G4 late findings: ${lateTotal}/${findingTotal}`
      : '  G4 NOT MEASURABLE — needs the first draft on disk',
  )
}

// ------------------------------------------------------------- §6.2 self-test

/**
 * What the committed run is known to have done, from its own files.
 *
 * LOOP-003 §6.2 also fixes two line counts — two for chapter 2 and one for
 * chapter 3. Those are NOT asserted here, and the reason is the finding this
 * instrument was written to produce: that run kept only its accepted drafts, so
 * there is nothing to diff and the numbers cannot be recovered from disk. They
 * are recorded below as unmeasurable rather than quietly dropped, because a
 * self-test that silently checks five of seven things is worse than one that
 * says which two it skipped and why.
 */
const SELF_TEST = {
  slug: 'deep-space-salvage-derelict',
  expect: [
    ['chapter 1 passes on the first attempt', (r) => r.chapters[0].passedAt === 1],
    ['chapter 2 passes on the second', (r) => r.chapters[1].passedAt === 2],
    ['chapter 2 resolved 3 findings', (r) => r.chapters[1].attempts[1].resolved === 3],
    ['chapter 3 passes on the second', (r) => r.chapters[2].passedAt === 2],
    ['chapter 3 resolved 1 finding', (r) => r.chapters[2].attempts[1].resolved === 1],
    ['chapter 3 had 1 overruled', (r) => r.chapters[2].attempts[0].overruledCount === 1],
  ],
  unmeasurable: [
    'chapter 2 touched 2 lines — the rejected draft was not kept',
    'chapter 3 touched 1 line — the rejected draft was not kept',
  ],
}

function selfTest() {
  // The committed run predates the fifth characteristic, so `outline` has no
  // critique file and every attempt is "unscored" on it. The self-test asks
  // about the four that existed; a run measured against five is the point of
  // the loop, not of its instrument.
  const original = FEATURES.splice(FEATURES.indexOf('outline'), 1)
  let failures = 0
  try {
    const result = measureRun(SELF_TEST.slug)
    for (const [name, check] of SELF_TEST.expect) {
      let ok = false
      let detail = ''
      try {
        ok = check(result)
      } catch (err) {
        detail = ` (${err.message})`
      }
      if (!ok) failures += 1
      console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail}`)
    }
    for (const note of SELF_TEST.unmeasurable) console.log(`SKIP  ${note}`)
  } finally {
    FEATURES.push(...original)
  }

  console.log(
    failures
      ? `\n${failures} check(s) failed — the instrument does not reproduce the run, so do not trust it`
      : `\nthe instrument reproduces the committed run (${SELF_TEST.unmeasurable.length} assertions skipped, named above)`,
  )
  return failures
}

// ------------------------------------------------------------------- main

const arg = process.argv[2]
if (!arg) {
  console.log('usage: node measure.mjs <slug> | --self-test')
  process.exit(2)
} else if (arg === '--self-test') {
  process.exit(selfTest() ? 1 : 0)
} else {
  report(arg)
}
