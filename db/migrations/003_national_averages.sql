-- 003: nationwide inspection counts, computed by us from FMCSA's public inspection data.
-- Counts are stored rather than percentages, so the rate can always be shown with its evidence.
create table national_averages (
    period_end              date primary key,
    period_start            date not null,
    driver_inspections      integer not null,
    driver_oos_inspections  integer not null,
    vehicle_inspections     integer not null,
    vehicle_oos_inspections integer not null,
    computed_at             timestamptz not null default now()
);
