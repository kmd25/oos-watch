import type { TopViolation } from './api'

const dateFormat = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' })

// A violation code starts with the part of the federal safety regulations (49 CFR) it
// comes from, e.g. "393.47E" is part 393. This says in plain words what each part covers.
const PART_NAMES: Record<string, string> = {
  '382': 'Drug and alcohol testing',
  '383': 'Commercial driver’s license',
  '390': 'General rules',
  '391': 'Driver qualification',
  '392': 'Driving rules',
  '393': 'Vehicle parts and equipment',
  '395': 'Hours of service',
  '396': 'Inspection and maintenance',
  '397': 'Hazardous materials driving and parking',
}

function partName(code: string) {
  return PART_NAMES[code.slice(0, 3)]
}

export function TopViolations({ violations }: { violations: TopViolation[] }) {
  // Every bar is drawn against the largest count, so the longest bar fills the track.
  const largest = Math.max(...violations.map((violation) => violation.violations))

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h2 className="font-semibold">Most frequent violations</h2>
      <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-secondary">
        Last 24 months
        <span className="flex items-center gap-2">
          <span className="size-3 rounded-sm bg-series-2" /> Out of service
        </span>
        <span className="flex items-center gap-2">
          <span className="size-3 rounded-sm bg-series-1" /> Other
        </span>
      </p>

      {violations.length === 0 && <p className="mt-3 text-sm text-ink-secondary">No violations in this period.</p>}

      <ol className="mt-3 divide-y divide-border">
        {violations.map((violation) => (
          <li key={violation.viol_code} className="grid gap-x-4 gap-y-2 py-3 sm:grid-cols-[1fr_16rem]">
            <div>
              <p>{violation.viol_desc ?? violation.viol_code}</p>
              <p className="text-sm text-ink-secondary">
                {[partName(violation.viol_code), violation.viol_code].filter(Boolean).join(' · ')}
              </p>
            </div>

            <div>
              {/* The bar: an out-of-service part and the rest, sized as shares of the largest count. */}
              <div className="flex items-center gap-2">
                <div className="flex h-2 flex-1 gap-0.5">
                  {violation.oos_violations > 0 && (
                    <div
                      className="rounded-full bg-series-2"
                      style={{ width: `${(violation.oos_violations / largest) * 100}%` }}
                    />
                  )}
                  {violation.violations > violation.oos_violations && (
                    <div
                      className="rounded-full bg-series-1"
                      style={{ width: `${((violation.violations - violation.oos_violations) / largest) * 100}%` }}
                    />
                  )}
                </div>
                <span className="w-6 text-right font-semibold tabular-nums">{violation.violations}</span>
              </div>
              <p className="mt-1 text-sm text-ink-secondary">
                {violation.oos_violations > 0 && `${violation.oos_violations} out of service · `}
                {violation.inspections} {violation.inspections === 1 ? 'inspection' : 'inspections'} · last{' '}
                {dateFormat.format(new Date(violation.latest_date))}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
