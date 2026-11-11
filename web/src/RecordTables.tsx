import { useState } from 'react'
import type { Crash, Inspection } from './api'

const dateFormat = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' })

function formatDate(value: string) {
  return dateFormat.format(new Date(value))
}

// FMCSA's inspection levels, from its data dictionary.
const LEVEL_NAMES: Record<number, string> = {
  1: 'Full',
  2: 'Walk-around',
  3: 'Driver only',
  4: 'Special study',
  5: 'Terminal',
  6: 'Radioactive materials',
}

// Class names shared by both tables, so they look the same.
const HEAD = 'px-3 py-2 text-left font-medium whitespace-nowrap'
const CELL = 'px-3 py-2 whitespace-nowrap'
const NUMBER = 'text-right tabular-nums'

const SHOWN_AT_FIRST = 10

/** The card around a table. A wide table scrolls sideways inside it, not the whole page. */
function TableCard({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h2 className="font-semibold">{title}</h2>
      {note && <p className="mt-1 text-sm text-ink-secondary">{note}</p>}
      <div className="mt-3 overflow-x-auto">{children}</div>
    </section>
  )
}

export function InspectionTable({ inspections }: { inspections: Inspection[] }) {
  // Remembers whether the user has asked to see every row.
  const [showAll, setShowAll] = useState(false)
  const shown = showAll ? inspections : inspections.slice(0, SHOWN_AT_FIRST)
  const mismatches = inspections.filter((inspection) => inspection.oos_mismatch).length

  return (
    <TableCard
      title="Inspections"
      note={
        mismatches > 0
          ? `⚠ marks ${mismatches} inspections where FMCSA's out-of-service total disagrees with its own list of violations. The total is what FMCSA publishes.`
          : undefined
      }
    >
      <table className="w-full text-sm">
        <thead className="text-ink-secondary">
          <tr>
            <th className={HEAD}>Date</th>
            <th className={HEAD}>State</th>
            <th className={HEAD}>Report</th>
            <th className={HEAD}>Level</th>
            <th className={HEAD}>Location</th>
            <th className={`${HEAD} ${NUMBER}`}>Violations</th>
            <th className={`${HEAD} ${NUMBER}`}>Out of service</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((inspection) => (
            <tr key={inspection.inspection_id} className="border-t border-border">
              <td className={CELL}>{formatDate(inspection.insp_date)}</td>
              <td className={CELL}>{inspection.report_state}</td>
              <td className={CELL}>{inspection.report_number}</td>
              <td className={CELL}>{LEVEL_NAMES[inspection.insp_level_id] ?? inspection.insp_level_id}</td>
              <td className={CELL}>{inspection.location_desc ?? '—'}</td>
              <td className={`${CELL} ${NUMBER}`}>{inspection.viol_total}</td>
              <td className={`${CELL} ${NUMBER}`}>
                {inspection.oos_mismatch && (
                  <span className="mr-2 text-ink-secondary">⚠ {inspection.oos_violation_rows} in the list</span>
                )}
                {inspection.oos_total}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {inspections.length > SHOWN_AT_FIRST && (
        <button
          className="mt-3 rounded-md border border-border px-3 py-1 text-sm hover:bg-page"
          onClick={() => setShowAll(!showAll)}
        >
          {showAll ? 'Show fewer' : `Show all ${inspections.length}`}
        </button>
      )}
    </TableCard>
  )
}

export function CrashTable({ crashes }: { crashes: Crash[] }) {
  const duplicates = crashes.filter((crash) => crash.possible_duplicate).length

  return (
    <TableCard
      title="Crash records"
      note={
        duplicates > 0
          ? `⚠ marks ${duplicates} records for the same vehicle on the same day. They may be one crash reported twice; FMCSA counts each one.`
          : undefined
      }
    >
      <table className="w-full text-sm">
        <thead className="text-ink-secondary">
          <tr>
            <th className={HEAD}>Date</th>
            <th className={HEAD}>Time</th>
            <th className={HEAD}>State</th>
            <th className={HEAD}>Place</th>
            <th className={`${HEAD} ${NUMBER}`}>Vehicles</th>
            <th className={`${HEAD} ${NUMBER}`}>Fatalities</th>
            <th className={`${HEAD} ${NUMBER}`}>Injuries</th>
            <th className={HEAD}>Towed</th>
          </tr>
        </thead>
        <tbody>
          {crashes.map((crash) => (
            <tr key={crash.crash_id} className="border-t border-border">
              <td className={CELL}>
                {formatDate(crash.report_date)}
                {crash.possible_duplicate && <span className="ml-2 text-ink-secondary">⚠ possible duplicate</span>}
              </td>
              <td className={CELL}>{crash.report_time?.slice(0, 5) ?? '—'}</td>
              <td className={CELL}>{crash.report_state}</td>
              {/* Place names can be long, so this one cell is allowed to wrap. */}
              <td className="px-3 py-2">{[crash.city, crash.location].filter(Boolean).join(', ') || '—'}</td>
              <td className={`${CELL} ${NUMBER}`}>{crash.vehicles_in_accident ?? '—'}</td>
              <td className={`${CELL} ${NUMBER}`}>{crash.fatalities}</td>
              <td className={`${CELL} ${NUMBER}`}>{crash.injuries}</td>
              <td className={CELL}>{crash.tow_away === null ? '—' : crash.tow_away ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {crashes.length === 0 && <p className="text-sm text-ink-secondary">No crash records.</p>}
    </TableCard>
  )
}
