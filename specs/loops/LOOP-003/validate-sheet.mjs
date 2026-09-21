#!/usr/bin/env node
/**
 * LOOP-003 §3 — the sheet validator. Nothing goes to the writer without it.
 *
 * The loop's whole claim is that each failed attempt makes the next one easier
 * rather than merely better informed, and that claim rests entirely on the
 * sheet being complete every time. A sheet missing its scores, or a finding
 * missing its quote, does not degrade the redraft a little — it returns the
 * writer to guessing, which is the state attempt 1 was already in.
 *
 * So this is a gate on the instrument, not a lint. §8.3 forbids sending a sheet
 * that does not pass, and forbids trimming findings to make one shorter.
 *
 *   node validate-sheet.mjs <file.md> [--attempt 3]
 *   node validate-sheet.mjs --self-test
 *
 * Exit 0 when the sheet may be sent, 1 when it may not, and the reasons are
 * printed either way.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))

export const REQUIRED_BLOCKS = [
  'SCORES FROM THE PREVIOUS ATTEMPT',
  'DO NOT TOUCH',
  'OPEN',
  'RESOLVED',
  'RULE:',
]

/** §3 rule 3 — four fields or it is not a finding. */
export const FINDING_FIELDS = ['Quote:', 'What is wrong:', 'Against what:', 'How it should read:']

export function validateSheet(text, { attempt } = {}) {
  const problems = []

  for (const block of REQUIRED_BLOCKS) {
    if (!text.includes(block)) problems.push(`missing block: ${block}`)
  }

  const header = /CHAPTER\s+(\d+)\s+—\s+ATTEMPT\s+([123])\s+OF\s+3/.exec(text)
  if (!header) problems.push('no "CHAPTER n — ATTEMPT k OF 3" header')
  const k = attempt ?? (header ? Number(header[2]) : null)

  // §3 rule 1 — all five scores, including the passing ones. A writer that
  // cannot see what is already right will improve it.
  const FIVE = ['Continuity', 'Science', 'Outline', 'Length', 'Heading']
  for (const feature of FIVE) {
    if (!new RegExp(`${feature}\\s+(\\d+|—)`).test(text)) {
      problems.push(`score not shown for: ${feature}`)
    }
  }

  // Findings are numbered items; each needs its four fields.
  const items = text.split(/\n\s{2}\d+\.\s/).slice(1)
  if (!items.length) problems.push('no findings — a sheet is only sent when something failed')
  items.forEach((item, i) => {
    for (const field of FINDING_FIELDS) {
      if (!item.includes(field)) problems.push(`finding ${i + 1}: missing "${field}"`)
    }
    const quote = /Quote:\s*"([^"]*)"/.exec(item)
    if (quote && quote[1].trim().length < 8) {
      problems.push(`finding ${i + 1}: quote is too short to be literal`)
    }
    // §8.3 — the "against what" points at the Bible or the outline. Never at a
    // previous chapter: the writer has never seen one and this sheet is not
    // the hole through which it finally does.
    const against = /Against what:\s*(.+)/.exec(item)
    if (against && /\bch(apter)?\s*\d|ch\d{2}\.md/i.test(against[1])) {
      problems.push(`finding ${i + 1}: "Against what" cites a chapter, not the Bible or the outline`)
    }
  })

  // §2 — the third attempt is the one that does not require interpretation.
  if (k === 3) {
    items.forEach((item, i) => {
      if (!item.includes('Replacement:')) {
        problems.push(`finding ${i + 1}: attempt 3 needs a literal "Replacement:"`)
      }
    })
  } else if (k !== null && text.includes('Replacement:')) {
    problems.push(`attempt ${k} must not carry a literal replacement — that is attempt 3's escalation`)
  }

  // An unsubstituted template is the failure this catches most often.
  const slot = /\{[a-z][^}\n]*\}/i.exec(text)
  if (slot) problems.push(`template slot left unfilled: ${slot[0]}`)

  return { ok: problems.length === 0, problems }
}

// ------------------------------------------------------------------ self-test

const GOOD = `CHAPTER 2 — ATTEMPT 2 OF 3

SCORES FROM THE PREVIOUS ATTEMPT
  Continuity 7 · Science 8 · Outline 10 · Length 10 · Heading 10
  The lowest is 7. All five must reach 8.

DO NOT TOUCH — these passed, and changing them can only cost you:
  Science · Outline · Length · Heading

OPEN — Continuity (1 finding, worst first)
  1. [medium] Timeline arithmetic
     Quote:        "Drafted 0118 ship time, nine hours out, received 1912."
     What is wrong: 0118 to 1912 is eighteen hours, not nine.
     Against what:  bible/timeline.md, Day 2 — the offer arrives eighteen hours stale.
     How it should read: flight time plus time queued at the relay must total eighteen.

RESOLVED since the last attempt:
  (none — this is the first correction)

RULE: change only the lines quoted above.
`

function selfTest() {
  const cases = [
    ['a complete attempt-2 sheet passes', GOOD, {}, true],
    [
      'a sheet missing a score is refused',
      GOOD.replace(' · Outline 10', ''),
      {},
      false,
    ],
    [
      'a finding missing "Against what" is refused',
      GOOD.replace(/     Against what:.*\n/, ''),
      {},
      false,
    ],
    [
      'a sheet citing a previous chapter is refused',
      GOOD.replace('bible/timeline.md, Day 2', 'chapter 1'),
      {},
      false,
    ],
    [
      'attempt 3 without a literal replacement is refused',
      GOOD.replace('ATTEMPT 2 OF 3', 'ATTEMPT 3 OF 3'),
      {},
      false,
    ],
    [
      'attempt 2 carrying a literal replacement is refused',
      GOOD.replace(
        '     How it should read: flight',
        '     Replacement:   "..."\n     How it should read: flight',
      ),
      {},
      false,
    ],
    [
      'an unfilled template slot is refused',
      GOOD.replace('Continuity 7', 'Continuity {c}'),
      {},
      false,
    ],
    ['the shipped template is not a sendable sheet', fs.readFileSync(path.join(HERE, 'sheet_template', 'v01.md'), 'utf8'), {}, false],
  ]

  let failures = 0
  for (const [name, text, opts, expected] of cases) {
    const { ok, problems } = validateSheet(text, opts)
    const right = ok === expected
    if (!right) failures += 1
    console.log(
      `${right ? 'PASS' : 'FAIL'}  ${name}${right || ok ? '' : ` -> ${problems.join('; ')}`}`,
    )
  }
  console.log(failures ? `\n${failures} failed` : '\nthe validator behaves')
  return failures
}

const arg = process.argv[2]
if (arg === '--self-test') {
  process.exit(selfTest() ? 1 : 0)
} else if (!arg) {
  console.log('usage: node validate-sheet.mjs <file.md> [--attempt 3] | --self-test')
  process.exit(2)
} else {
  const attemptFlag = process.argv.indexOf('--attempt')
  const { ok, problems } = validateSheet(fs.readFileSync(arg, 'utf8'), {
    attempt: attemptFlag > 0 ? Number(process.argv[attemptFlag + 1]) : undefined,
  })
  if (ok) {
    console.log(`${arg}: complete — send it`)
  } else {
    console.log(`${arg}: DO NOT SEND`)
    for (const p of problems) console.log(`  - ${p}`)
  }
  process.exit(ok ? 0 : 1)
}
