import { ArrowDownRightIcon, ArrowUpRightIcon } from '@heroicons/react/20/solid'
import { cn } from '../../utils/cn'
import { formatNumber } from '../../utils/format'

const GRADIENTS = {
  brand: 'from-brand-500 to-violet-600',
  blue: 'from-blue-500 to-cyan-500',
  green: 'from-emerald-500 to-teal-500',
  amber: 'from-amber-500 to-orange-500',
  red: 'from-rose-500 to-red-500',
  slate: 'from-slate-600 to-slate-800',
}

/**
 * Gradient statistics card.
 *   gradient: render the whole card as a gradient (hero metric)
 *   else: white card with a colored icon chip.
 */
export default function StatCard({
  label,
  value,
  icon: Icon,
  color = 'brand',
  delta,
  gradient = false,
  loading = false,
}) {
  if (gradient) {
    return (
      <div
        className={cn(
          'relative overflow-hidden rounded-2xl bg-gradient-to-br p-5 text-white shadow-card',
          GRADIENTS[color],
        )}
      >
        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10" />
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-white/80">{label}</p>
          {Icon && <Icon className="h-5 w-5 text-white/80" />}
        </div>
        <p className="mt-3 text-3xl font-bold">
          {loading ? '—' : formatNumber(value)}
        </p>
        {delta != null && <DeltaPill delta={delta} light />}
      </div>
    )
  }

  return (
    <div className="card-base p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {loading ? '—' : formatNumber(value)}
          </p>
        </div>
        {Icon && (
          <span
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-sm',
              GRADIENTS[color],
            )}
          >
            <Icon className="h-5 w-5" />
          </span>
        )}
      </div>
      {delta != null && <DeltaPill delta={delta} />}
    </div>
  )
}

function DeltaPill({ delta, light }) {
  const up = delta >= 0
  const Icon = up ? ArrowUpRightIcon : ArrowDownRightIcon
  return (
    <div className="mt-3 flex items-center gap-1.5 text-xs font-medium">
      <span
        className={cn(
          'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5',
          light
            ? 'bg-white/20 text-white'
            : up
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400'
              : 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400',
        )}
      >
        <Icon className="h-3 w-3" />
        {Math.abs(delta)}%
      </span>
      <span className={light ? 'text-white/70' : 'text-gray-400'}>vs last period</span>
    </div>
  )
}
