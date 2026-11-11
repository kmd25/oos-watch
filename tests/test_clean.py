from datetime import date, time

import pytest

from ingest import clean


def test_inspection_text_becomes_typed_values(inspections):
    row = clean.clean_inspection(inspections[0])

    assert row["inspection_id"] == 1
    assert row["insp_date"] == date(2026, 1, 15)
    assert row["insp_start_time"] == time(9, 30)
    assert row["insp_level_id"] == 1
    assert row["gross_comb_veh_wt"] == 80000
    assert row["viol_total"] == 2
    assert row["vehicle_oos_total"] == 1


def test_leading_zeros_are_kept(inspections, violations):
    assert clean.clean_inspection(inspections[1])["report_number"] == "0000000002"
    assert clean.clean_violation(violations[1])["citation_number"] == "00123"


def test_missing_optional_fields_become_none(inspections):
    row = clean.clean_inspection(inspections[1])

    assert row["insp_start_time"] is None
    assert row["location_desc"] is None
    assert row["gross_comb_veh_wt"] is None


def test_missing_required_field_fails(inspections):
    del inspections[0]["insp_date"]

    with pytest.raises(KeyError):
        clean.clean_inspection(inspections[0])


def test_raw_keeps_the_whole_original_row(inspections):
    row = clean.clean_inspection(inspections[0])

    assert row["raw"]["insp_carrier_name"] == "FAKE TEST CARRIER"


def test_violation_out_of_service_becomes_boolean(violations):
    assert clean.clean_violation(violations[0])["out_of_service"] is True
    assert clean.clean_violation(violations[1])["out_of_service"] is False


def test_out_of_service_z_means_yes_and_missing_means_unknown(violations):
    violations[0]["out_of_service_indicator"] = "Z"
    del violations[1]["out_of_service_indicator"]

    assert clean.clean_violation(violations[0])["out_of_service"] is True
    assert clean.clean_violation(violations[1])["out_of_service"] is None


def test_unexpected_out_of_service_value_fails(violations):
    violations[0]["out_of_service_indicator"] = "X"

    with pytest.raises(KeyError):
        clean.clean_violation(violations[0])


def test_violation_code_is_stored_as_sent(violations):
    row = clean.clean_violation(violations[0])

    assert row["viol_code"] == "393.75C"
    assert row["insp_unit_id"] == 500
    assert clean.clean_violation(violations[1])["insp_unit_id"] is None


def test_sms_gets_the_fetch_date(sms):
    row = clean.clean_sms(sms[0], date(2026, 11, 10))

    assert row["fetched_on"] == date(2026, 11, 10)
    assert row["insp_total"] == 2
    assert row["vehicle_oos_insp_total"] == 1


def test_dedupe_keeps_the_later_row():
    rows = [{"id": "1", "v": "old"}, {"id": "2", "v": "b"}, {"id": "1", "v": "new"}]

    assert clean.dedupe(rows, "id") == [{"id": "1", "v": "new"}, {"id": "2", "v": "b"}]


def test_crash_text_becomes_typed_values(crashes):
    row = clean.clean_crash(crashes[0])

    assert row["crash_id"] == 1
    assert row["report_date"] == date(2026, 3, 10)
    assert row["report_time"] == time(1, 17)
    assert (row["fatalities"], row["injuries"], row["vehicles_in_accident"]) == (0, 1, 2)
    assert (row["tow_away"], row["hazmat_released"]) == (True, False)
    assert row["vin"] == "FAKEVIN0000000001"


def test_crash_with_only_the_required_fields(crashes):
    row = clean.clean_crash(crashes[1])

    assert row["report_time"] is None
    assert row["tow_away"] is None
    assert row["vin"] is None
