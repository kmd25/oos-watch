-- 004: crashes reported to FMCSA by state police (public MCMIS Crash File).
-- One row is one of the carrier's vehicles in a crash, keyed by FMCSA's own ID.
-- Column names follow the source so that each one matches its key in `raw`.
create table crashes (
    crash_id             bigint primary key,
    dot_number           text not null references carriers (dot_number),
    report_state         text not null,
    report_number        text not null,
    report_seq_no        smallint not null,
    report_date          date not null,  -- the date of the crash, despite the name
    report_time          time,
    city                 text,
    location             text,
    fatalities           smallint not null,
    injuries             smallint not null,
    tow_away             boolean,
    hazmat_released      boolean,
    federal_recordable   boolean,
    vehicles_in_accident smallint,
    vin                  text,
    raw                  jsonb not null,
    first_seen_at        timestamptz not null default now(),
    last_seen_at         timestamptz not null default now()
);

create index crashes_dot_number_report_date_idx on crashes (dot_number, report_date);
