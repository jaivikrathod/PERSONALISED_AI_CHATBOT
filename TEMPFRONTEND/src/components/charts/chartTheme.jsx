// Shared Recharts styling so every chart matches the design system
// and reads well in dark mode.

export const axisProps = {
  tick: { fontSize: 12, fill: '#94a3b8' },
  axisLine: false,
  tickLine: false,
}

export const gridProps = {
  strokeDasharray: '3 3',
  stroke: 'rgba(148,163,184,0.18)',
  vertical: false,
}

export const CHART_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6']

/** Custom tooltip card used across all charts. */
export function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow-card-hover dark:border-gray-700 dark:bg-gray-900">
      {label != null && (
        <p className="mb-1 font-medium text-gray-700 dark:text-gray-200">{label}</p>
      )}
      {payload.map((entry) => (
        <div key={entry.dataKey || entry.name} className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: entry.color || entry.fill }}
          />
          <span className="capitalize text-gray-500 dark:text-gray-400">
            {entry.name}:
          </span>
          <span className="font-semibold text-gray-800 dark:text-gray-100">
            {entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}
