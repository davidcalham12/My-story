import { Provenance } from '@/shared/ui/Provenance'
import { usd } from './lib'
import type { CostTotal } from './model'

const plural = (n: number) => (n === 1 ? '' : 's')

/** The novel's total on its Library card: the local record, with its provenance. */
export function CostTotalLine({ total }: { total: CostTotal | undefined }) {
  if (!total) return null
  return (
    <p className="hint">
      Total cost: {usd(total.usd)} <Provenance grade={total.provenance} /> {total.provenance}, {total.source}
      {total.absent > 0 && ` · ${total.absent} change${plural(total.absent)} not measured`}
    </p>
  )
}
