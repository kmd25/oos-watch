-- 001_init: tables for public FMCSA data.
-- Accounts and companies come in a later migration, with the login work.

-- Every DOT number we ingest data for. Ingest loops over this table.
create table carriers (
    dot_number text primary key,
    added_at   timestamptz not null default now()
);

-- One row per roadside inspection, keyed by FMCSA's own ID.
create table inspections (
    inspection_id      bigint primary key,
    dot_number         text not null references carriers (dot_number),
    report_state       text not null,
    report_number      text not null,
    insp_date          date not null,
    insp_start_time    time,
    insp_end_time      time,
    insp_level_id      smallint not null,
    location_desc      text,
    county_code_state  text,
    post_acc_ind       text,
    gross_comb_veh_wt  integer,
    viol_total         smallint not null,
    oos_total          smallint not null,
    driver_viol_total  smallint not null,
    driver_oos_total   smallint not null,
    vehicle_viol_total smallint not null,
    vehicle_oos_total  smallint not null,
    hazmat_viol_total  smallint not null,
    hazmat_oos_total   smallint not null,
    raw                jsonb not null,
    first_seen_at      timestamptz not null default now(),
    last_seen_at       timestamptz not null default now()
);

-- Almost every dashboard query is "this carrier, ordered or grouped by date".
create index inspections_dot_number_insp_date_idx on inspections (dot_number, insp_date);

-- One row per violation found during an inspection.
create table violations (
    insp_violation_id bigint primary key,
    inspection_id     bigint not null references inspections (inspection_id),
    seq_no            smallint,
    viol_code         text not null,
    viol_desc         text,
    part_no           text,
    part_no_section   text,
    insp_viol_unit    text not null,
    insp_unit_id      bigint,
    out_of_service    boolean not null,
    citation_number   text,
    raw               jsonb not null,
    first_seen_at     timestamptz not null default now(),
    last_seen_at      timestamptz not null default now()
);

-- Postgres does not index foreign keys automatically; joins to inspections need this.
create index violations_inspection_id_idx on violations (inspection_id);

-- FMCSA's published SMS figures. The source has no date, so we stamp the fetch date.
create table sms_snapshots (
    id                     bigint generated always as identity primary key,
    dot_number             text not null references carriers (dot_number),
    fetched_on             date not null,
    insp_total             integer,
    driver_insp_total      integer,
    driver_oos_insp_total  integer,
    vehicle_insp_total     integer,
    vehicle_oos_insp_total integer,
    raw                    jsonb not null,
    unique (dot_number, fetched_on)
);
