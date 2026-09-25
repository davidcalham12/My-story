import type { ChangeCost } from './model'

/** Every number goes through the provenance helpers: absent is a word, never 0. */
export { usd, minutes } from '@/shared/lib/provenance'

const KIND: Record<string, string> = {
  generate: 'First generation',
  continue: 'Continuation',
  reader_change: 'Reader change',
  redo: 'Chapter redone',
}

/** "Reader change · v3 · ch 3, 10" */
export function what(row: ChangeCost): string {
  const parts = [KIND[row.kind] ?? row.kind]
  if (row.version !== null) parts.push(`v${row.version}`)
  if (row.chapters?.length) parts.push(`ch ${row.chapters.join(', ')}`)
  return parts.join(' · ')
}

/** `claude-opus-5[1m]` → `Opus 5`; the full id stays in the title attribute. */
export function family(model: string | null): string {
  if (!model) return ''
  return model.split(', ').map((m) => {
    const hit = /(opus|sonnet|haiku)-?([\d-]*)/i.exec(m)
    const word = hit?.[1]
    if (!word) return m
    const name = word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    const version = (hit[2] ?? '').split('-').filter((p) => p && p.length < 3).join('.')
    return version ? `${name} ${version}` : name
  }).join(', ')
}

export const when = (iso: string | null): string =>
  iso ? iso.slice(0, 16).replace('T', ' ') : 'not recorded'
