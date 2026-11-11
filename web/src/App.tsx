import { useEffect, useState } from 'react'
import { getJson, type Crash, type Inspection, type Summary, type TopViolation, type TrendMonth } from './api'
import { CrashTable, InspectionTable } from './RecordTables'
import { SummaryCard } from './SummaryCard'
import { TopViolations } from './TopViolations'
import { TrendChart } from './TrendChart'

function App() {
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
    getJson<Summary>('/summary').then(setSummary).catch(fail)
    getJson<TrendMonth[]>('/trends').then(setMonths).catch(fail)
    getJson<TopViolation[]>('/violations/top').then(setViolations).catch(fail)
    getJson<Inspection[]>('/inspections').then(setInspections).catch(fail)
    getJson<Crash[]>('/crashes').then(setCrashes).catch(fail)
  }, [])

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-semibold">OOS Watch</h1>
      <div className="mt-4 space-y-6">
        {error && <p className="text-critical">Could not load the data: {error}</p>}
        {!error && !summary && <p className="text-ink-secondary">Loading…</p>}
        {summary && <SummaryCard summary={summary} />}
        {months && <TrendChart months={months} />}
        {violations && <TopViolations violations={violations} />}
        {inspections && <InspectionTable inspections={inspections} />}
        {crashes && <CrashTable crashes={crashes} />}
      </div>
    </main>
  )
}

export default App
