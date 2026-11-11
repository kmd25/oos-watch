import { Bar, BarChart, CartesianGrid, Rectangle, Tooltip, XAxis, YAxis } from 'recharts'
import type { TrendMonth } from './api'

const monthFormat = new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' })

function formatMonth(value: string) {
  return monthFormat.format(new Date(value))
}

// What one column of the chart is drawn from: a month split into two stacked parts.
type Column = TrendMonth & { clean: number }

const SERIES = [
  { key: 'oos_inspections', label: 'With an out-of-service violation', color: 'var(--series-2)' },
  { key: 'clean', label: 'No out-of-service violation', color: 'var(--series-1)' },
] as const

/** The small box that follows the pointer: every number for the month under it. */
function MonthTooltip({ active, payload }: { active?: boolean; payload?: { payload: Column }[] }) {
  if (!active || !payload?.length) return null
  const month = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-surface p-3 text-sm shadow-sm">
      <p className="font-medium">{formatMonth(month.month)}</p>
      <p className="mt-1">
        <strong>{month.inspections}</strong> <span className="text-ink-secondary">inspections</span>
      </p>
      {SERIES.map((series) => (
        <p key={series.key} className="flex items-center gap-2">
          <span className="h-0.5 w-3" style={{ background: series.color }} />
          <strong>{month[series.key]}</strong>
          <span className="text-ink-secondary">{series.label.toLowerCase()}</span>
        </p>
      ))}
      <p>
        <strong>{month.violations}</strong> <span className="text-ink-secondary">violations</span>
      </p>
    </div>
  )
}

export function TrendChart({ months }: { months: TrendMonth[] }) {
  const columns: Column[] = months.map((month) => ({ ...month, clean: month.inspections - month.oos_inspections }))

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h2 className="font-semibold">Inspections per month</h2>

      {/* The legend: which color is which. */}
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-secondary">
        {SERIES.map((series) => (
          <li key={series.key} className="flex items-center gap-2">
            <span className="size-3 rounded-sm" style={{ background: series.color }} />
            {series.label}
          </li>
        ))}
      </ul>

      <div className="mt-3 h-64">
        {/* `responsive` makes the chart follow the size of the box it sits in. */}
        <BarChart
          responsive
          style={{ width: '100%', height: '100%' }}
          data={columns}
          margin={{ top: 8, right: 8, bottom: 0, left: -24 }}
        >
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis
            dataKey="month"
            tickFormatter={formatMonth}
            minTickGap={32}
            tickLine={false}
            axisLine={{ stroke: 'var(--grid)' }}
            tick={{ fill: 'var(--ink-secondary)', fontSize: 12 }}
          />
          <YAxis
            allowDecimals={false}
            tickLine={false}
            axisLine={false}
            tick={{ fill: 'var(--ink-secondary)', fontSize: 12 }}
          />
          <Tooltip content={<MonthTooltip />} cursor={{ fill: 'var(--grid)', opacity: 0.5 }} />
          {/* Both bars share stackId, so they sit on top of each other. The out-of-service
              part is at the bottom, where every month starts from the same line and can be
              compared. Only the top end of a column is rounded. The stroke in the surface
              color leaves a thin gap between the two parts. */}
          <Bar
            dataKey="oos_inspections"
            stackId="month"
            fill="var(--series-2)"
            stroke="var(--surface)"
            strokeWidth={2}
            maxBarSize={24}
            isAnimationActive={false}
            shape={(props: any) => <Rectangle {...props} radius={props.payload.clean === 0 ? [4, 4, 0, 0] : 0} />}
          />
          <Bar
            dataKey="clean"
            stackId="month"
            fill="var(--series-1)"
            stroke="var(--surface)"
            strokeWidth={2}
            maxBarSize={24}
            isAnimationActive={false}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </div>

      {/* The same numbers as a table, for screen readers and for anyone who prefers rows. */}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-ink-secondary">Show as a table</summary>
        <table className="mt-2 w-full text-left tabular-nums">
          <thead className="text-ink-secondary">
            <tr>
              <th className="py-1 font-medium">Month</th>
              <th className="py-1 font-medium">Inspections</th>
              <th className="py-1 font-medium">With out-of-service</th>
              <th className="py-1 font-medium">Violations</th>
            </tr>
          </thead>
          <tbody>
            {[...months].reverse().map((month) => (
              <tr key={month.month} className="border-t border-border">
                <td className="py-1">{formatMonth(month.month)}</td>
                <td className="py-1">{month.inspections}</td>
                <td className="py-1">{month.oos_inspections}</td>
                <td className="py-1">{month.violations}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  )
}
