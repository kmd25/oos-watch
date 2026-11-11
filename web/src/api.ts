// The shapes of the JSON our API returns. If the API changes, change these to match,
// and TypeScript will point at every place in the app that needs updating.

export type RateBlock = {
  inspections: number
  oos_inspections: number
  oos_rate: number | null // a fraction (0.25 = 25%); null when there were no inspections
}

export type Rates = {
  period_start: string // dates arrive as text, e.g. "2026-11-11"
  period_end: string
  driver: RateBlock
  vehicle: RateBlock
}

export type Summary = {
  carrier: Rates
  national: Rates | null
  crashes: { crashes: number; fatal_crashes: number; injury_crashes: number }
  freshness: { last_ingest_at: string | null; latest_inspection_date: string | null }
}

export type TrendMonth = {
  month: string // the first day of the month, e.g. "2026-10-01"
  inspections: number
  violations: number
  oos_inspections: number // inspections with at least one out-of-service violation
  driver_inspections: number
  driver_oos_inspections: number
  vehicle_inspections: number
  vehicle_oos_inspections: number
}

export type TopViolation = {
  viol_code: string
  viol_desc: string | null
  violations: number
  oos_violations: number
  inspections: number // how many separate inspections the code appeared on
  latest_date: string
}

export type Inspection = {
  inspection_id: number
  insp_date: string
  report_state: string
  report_number: string
  insp_level_id: number
  location_desc: string | null
  viol_total: number
  oos_total: number
  driver_oos_total: number
  vehicle_oos_total: number
  oos_violation_rows: number // how many of its violation rows are marked out of service
  oos_mismatch: boolean // true when that count disagrees with oos_total
}

export type Crash = {
  crash_id: number
  report_date: string // the date of the crash
  report_time: string | null // e.g. "02:05:00"
  report_state: string
  city: string | null
  location: string | null
  fatalities: number
  injuries: number
  tow_away: boolean | null
  hazmat_released: boolean | null
  federal_recordable: boolean | null
  vehicles_in_accident: number | null
  possible_duplicate: boolean // same vehicle, same day as another row
}

/** GET a path from our API and return the parsed JSON, or throw if the request failed. */
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`)
  }
  return response.json()
}
