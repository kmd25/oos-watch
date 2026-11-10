"""Tests for the fetch code. requests.get is replaced, so nothing touches the network."""

import pytest

from ingest import fmcsa


class FakeResponse:
    def __init__(self, rows):
        self.rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self.rows


@pytest.fixture
def api(monkeypatch):
    """Stand in for the API: serves `api.rows` a page at a time and records each request."""

    class FakeApi:
        def __init__(self):
            self.rows = []
            self.calls = []

        def get(self, url, params, timeout):
            self.calls.append(params)
            start = params["$offset"]
            return FakeResponse(self.rows[start : start + params["$limit"]])

    fake = FakeApi()
    monkeypatch.setattr(fmcsa.requests, "get", fake.get)
    return fake


def test_fetch_all_follows_pages_until_a_short_one(api, monkeypatch):
    monkeypatch.setattr(fmcsa, "PAGE_SIZE", 2)
    api.rows = [{"n": str(n)} for n in range(5)]

    rows = fmcsa.fetch_all("dataset", {}, "n")

    assert rows == api.rows
    assert [call["$offset"] for call in api.calls] == [0, 2, 4]
    assert all(call["$order"] == "n" for call in api.calls)


def test_fetch_all_asks_once_more_when_the_last_page_is_full(api, monkeypatch):
    monkeypatch.setattr(fmcsa, "PAGE_SIZE", 2)
    api.rows = [{"n": str(n)} for n in range(4)]

    assert len(fmcsa.fetch_all("dataset", {}, "n")) == 4
    assert [call["$offset"] for call in api.calls] == [0, 2, 4]


def test_violations_are_requested_in_batches_of_ids(api, monkeypatch):
    monkeypatch.setattr(fmcsa, "ID_BATCH_SIZE", 2)

    fmcsa.fetch_violations(["1", "2", "3"])

    assert [call["$where"] for call in api.calls] == [
        "inspection_id in ('1', '2')",
        "inspection_id in ('3')",
    ]


def test_no_inspections_means_no_violation_requests(api):
    assert fmcsa.fetch_violations([]) == []
    assert api.calls == []


def test_dot_number_must_be_digits(api):
    with pytest.raises(ValueError):
        fmcsa.fetch_inspections("1 or 1=1")
    with pytest.raises(ValueError):
        fmcsa.fetch_sms("")
    assert api.calls == []
