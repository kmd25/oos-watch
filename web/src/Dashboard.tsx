import { useAuth } from '@clerk/react'
import { useEffect, useState } from 'react'
import { getJson, type Crash, type Inspection, type Summary, type TopViolation, type TrendMonth } from './api'
import { CrashTable, InspectionTable } from './RecordTables'
import { SummaryCard } from './SummaryCard'
import { TopViolations } from './TopViolations'
import { TrendChart } from './TrendChart'

export function Dashboard() {
  // Clerk hands out a fresh session token whenever we ask; they only last about a minute.
  const { getToken } = useAuth()

  // What the page knows: each piece of data once it has arrived, or an error message.
  const [summary, setSummary] = useState<Summary | null>(null)
  const [months, setMonths] = useState<TrendMonth[] | null>(null)
  const [violations, setViolations] = useState<TopViolation[] | null>(null)
  const [inspections, setInspections] = useState<Inspection[] | null>(null)
  const [crashes, setCrashes] = useState<Crash[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Runs once, after the page first appears: ask the API for the data.
  useEffect(() => {
    const fail = (problem: Error) => setError(problem.message)
    getJson<Summary>('/summary', getToken).then(setSummary).catch(fail)
    getJson<TrendMonth[]>('/trends', getToken).then(setMonths).catch(fail)
    getJson<TopViolation[]>('/violations/top', getToken).then(setViolations).catch(fail)
    getJson<Inspection[]>('/inspections', getToken).then(setInspections).catch(fail)
    getJson<Crash[]>('/crashes', getToken).then(setCrashes).catch(fail)
    // Run once only. Listing getToken here could re-run the requests on every redraw
    // if Clerk hands back a new function each time.
  }, [])

  return (
    <div className="space-y-6">
      {error && <p className="text-critical">Could not load the data: {error}</p>}
      {!error && !summary && <p className="text-ink-secondary">Loading…</p>}
      {summary && <SummaryCard summary={summary} />}
      {months && <TrendChart months={months} />}
      {violations && <TopViolations violations={violations} />}
      {inspections && <InspectionTable inspections={inspections} />}
      {crashes && <CrashTable crashes={crashes} />}
    </div>
  )
}
