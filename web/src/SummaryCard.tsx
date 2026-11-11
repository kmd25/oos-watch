import type { RateBlock, Summary } from './api'

const dateFormat = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' })

function formatDate(value: string | null) {
  return value ? dateFormat.format(new Date(value)) : 'never'
}

function formatPercent(rate: number) {
  return `${(rate * 100).toFixed(1)}%`
}

/** One headline number with a label above it and supporting lines below. */
function Tile({ label, value, children }: { label: string; value: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-sm text-ink-secondary">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value}</p>
      <div className="mt-2 space-y-1 text-sm text-ink-secondary">{children}</div>
    </div>
  )
}

/** "▲ 4.6 points above national (6.3%)". A higher out-of-service rate is worse. */
function Comparison({ rate, national }: { rate: number; national: number }) {
  const points = (rate - national) * 100
  const above = points > 0
  return (
    <p className={`font-medium ${above ? 'text-critical' : 'text-good'}`}>
      {above ? '▲' : '▼'} {Math.abs(points).toFixed(1)} points {above ? 'above' : 'below'} national (
      {formatPercent(national)})
    </p>
  )
}

function RateTile({ label, carrier, national }: { label: string; carrier: RateBlock; national?: RateBlock }) {
  return (
    <Tile label={label} value={carrier.oos_rate === null ? 'No data' : formatPercent(carrier.oos_rate)}>
      <p>
        {carrier.oos_inspections} of {carrier.inspections} inspections
      </p>
      {carrier.oos_rate !== null && national && national.oos_rate !== null && (
        <Comparison rate={carrier.oos_rate} national={national.oos_rate} />
      )}
    </Tile>
  )
}

export function SummaryCard({ summary }: { summary: Summary }) {
  const { carrier, national, crashes, freshness } = summary
  return (
    <section>
      <p className="text-sm text-ink-secondary">
        Last 24 months: {formatDate(carrier.period_start)} to {formatDate(carrier.period_end)}
      </p>

      <div className="mt-3 grid gap-4 sm:grid-cols-3">
        <RateTile label="Driver out-of-service rate" carrier={carrier.driver} national={national?.driver} />
        <RateTile label="Vehicle out-of-service rate" carrier={carrier.vehicle} national={national?.vehicle} />
        <Tile label="Crash records" value={String(crashes.crashes)}>
          <p>
            {crashes.fatal_crashes} fatal, {crashes.injury_crashes} with an injury
          </p>
        </Tile>
      </div>

      <p className="mt-4 text-sm text-ink-secondary">
        Data last checked {formatDate(freshness.last_ingest_at)}. Newest inspection{' '}
        {formatDate(freshness.latest_inspection_date)}.
      </p>
      <p className="mt-1 text-sm text-ink-secondary">
        Computed from public FMCSA data; this is not an official FMCSA record.
        {national &&
          ` National rates are computed from the same public data for ${formatDate(national.period_start)} to ${formatDate(national.period_end)}, and are not FMCSA's published averages.`}
      </p>
    </section>
  )
}
