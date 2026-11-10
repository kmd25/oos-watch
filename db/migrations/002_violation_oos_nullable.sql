-- 002: FMCSA leaves the out-of-service indicator empty on a small number of violations
-- (113 of 13.5 million on 2026-11-10). Store those as NULL ("unknown") instead of guessing.
alter table violations alter column out_of_service drop not null;
