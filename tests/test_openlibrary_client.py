"""Tests for the Open Library client (books/openlibrary.py).

Carried over from the original command-line script's tests. These never touch
the real internet: each test replaces `requests.get` with a fake that returns
a canned response or raises an error.
"""

import re

import pytest
import requests

from books import openlibrary


class FakeResponse:
    """Just enough of a requests.Response for search_books to use."""

    def __init__(self, status_code=200, json_data=None, invalid_json=False):
        self.status_code = status_code
        self._json_data = json_data
        self._invalid_json = invalid_json

    def json(self):
        if self._invalid_json:
            raise ValueError("not JSON")
        return self._json_data


DUNE = {
    "key": "/works/OL893414W",
    "title": "Dune",
    "author_name": ["Frank Herbert"],
    "first_publish_year": 1965,
    "cover_i": 11481354,
    "edition_count": 155,
    "isbn": [f"97800000000{n:02d}" for n in range(25)],
    "subject": [f"Subject {n}" for n in range(20)],
}


@pytest.fixture
def fake_get(monkeypatch):
    """Replace requests.get. Call it with a response or an exception to use."""
    calls = []

    def install(result):
        def fake(url, **kwargs):
            calls.append({"url": url, **kwargs})
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(openlibrary.requests, "get", fake)
        return calls

    return install


# --- Successful searches ----------------------------------------------------


def test_successful_search_sends_expected_request(fake_get):
    calls = fake_get(FakeResponse(json_data={"numFound": 1234, "docs": [DUNE]}))

    openlibrary.search_books("dune", contact_email="me@example.com")

    sent = calls[0]
    assert sent["url"] == openlibrary.SEARCH_URL
    assert sent["params"]["q"] == "dune"
    assert sent["params"]["page"] == 1
    assert sent["params"]["limit"] == 20
    assert sent["timeout"] == openlibrary.TIMEOUT_SECONDS
    assert sent["headers"]["User-Agent"] == "BookCatalogSystem/0.1 (me@example.com)"


def test_search_requests_only_the_needed_fields(fake_get):
    calls = fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    openlibrary.search_books("dune")

    requested = set(calls[0]["params"]["fields"].split(","))
    assert requested == {
        "key",
        "title",
        "author_name",
        "first_publish_year",
        "cover_i",
        "isbn",
        "subject",
        "edition_count",
    }


def test_search_passes_page_and_limit(fake_get):
    calls = fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    openlibrary.search_books("dune", page=3, limit=7)

    assert calls[0]["params"]["page"] == 3
    assert calls[0]["params"]["limit"] == 7


def test_user_agent_uses_the_configured_contact_email(fake_get, settings):
    settings.OPENLIBRARY_CONTACT_EMAIL = "configured@example.com"
    calls = fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    openlibrary.search_books("dune")

    assert "(configured@example.com)" in calls[0]["headers"]["User-Agent"]


def test_user_agent_without_a_contact_email(fake_get, settings):
    settings.OPENLIBRARY_CONTACT_EMAIL = ""
    calls = fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    openlibrary.search_books("dune")

    assert calls[0]["headers"]["User-Agent"] == "BookCatalogSystem/0.1"


def test_search_parses_results(fake_get):
    fake_get(FakeResponse(json_data={"numFound": 1234, "docs": [DUNE]}))

    page = openlibrary.search_books("dune")

    assert page.total == 1234
    [dune] = page.results
    assert dune.work_id == "OL893414W"
    assert dune.title == "Dune"
    assert dune.author_list == ["Frank Herbert"]
    assert dune.first_publish_year == 1965
    assert dune.cover_id == 11481354
    assert dune.cover_url_large == "https://covers.openlibrary.org/b/id/11481354-L.jpg"
    assert dune.edition_count == 155
    # Open Library can return hundreds; only the first 10 are kept.
    assert dune.isbns == DUNE["isbn"][:10]
    assert dune.subjects == DUNE["subject"][:10]


def test_search_fills_in_missing_fields_and_skips_docs_without_a_key(fake_get):
    docs = [{"key": "/works/OL1W"}, {"title": "No key"}, "not a dict"]
    fake_get(FakeResponse(json_data={"docs": docs}))

    page = openlibrary.search_books("anything")

    [result] = page.results
    assert result.work_id == "OL1W"
    assert result.title == "Untitled"
    assert result.author_list == []
    assert result.first_publish_year is None
    assert result.cover_id is None
    assert result.cover_url_large is None
    # Without numFound, the total falls back to the number of results.
    assert page.total == 1


def test_no_results(fake_get):
    fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    page = openlibrary.search_books("asdfghjkl")

    assert page.total == 0
    assert page.results == []


# --- Failures ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("result", "expected_message"),
    [
        (requests.exceptions.ConnectionError(), "Could not connect to Open Library"),
        (requests.exceptions.Timeout(), "did not respond within 10 seconds"),
        (requests.exceptions.TooManyRedirects(), "request to Open Library failed"),
        (FakeResponse(status_code=503), "unavailable right now (HTTP 503)"),
        (FakeResponse(status_code=429), "too many requests (HTTP 429)"),
        (FakeResponse(status_code=404), "rejected the request (HTTP 404)"),
        (FakeResponse(invalid_json=True), "wasn't valid JSON"),
        (FakeResponse(json_data={"error": "oops"}), "unexpected format"),
        (FakeResponse(json_data=["not", "a", "dict"]), "unexpected format"),
    ],
    ids=[
        "connection",
        "timeout",
        "other-request-error",
        "503",
        "429",
        "404",
        "bad-json",
        "bad-shape",
        "not-a-dict",
    ],
)
def test_failures_raise_search_error_with_specific_message(
    fake_get, result, expected_message
):
    fake_get(result)

    with pytest.raises(openlibrary.SearchError, match=re.escape(expected_message)):
        openlibrary.search_books("dune")


def test_network_failures_keep_the_technical_cause_for_logging(fake_get):
    original = requests.exceptions.ConnectionError("DNS lookup failed")
    fake_get(original)

    with pytest.raises(openlibrary.SearchError) as excinfo:
        openlibrary.search_books("dune")

    assert excinfo.value.__cause__ is original
    # The technical detail is not part of the message shown to users.
    assert "DNS" not in str(excinfo.value)


# --- Query cleaning ---------------------------------------------------------


@pytest.mark.parametrize(
    ("typed", "cleaned"),
    [
        ("978-0-441-01359-3", "9780441013593"),
        ("978 0 441 01359 3", "9780441013593"),
        ("  9780441013593  ", "9780441013593"),
        ("0-441-01359-7", "0441013597"),
        ("0-8044-2957-x", "080442957X"),
        ("dune", "dune"),
        ("  frank herbert  ", "frank herbert"),
        # Number-ish text that isn't ISBN-length is left alone.
        ("1984", "1984"),
        ("20 000 leagues", "20 000 leagues"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_clean_query(typed, cleaned):
    assert openlibrary.clean_query(typed) == cleaned


# --- Looking one work up by ID ----------------------------------------------


def test_fetch_work_searches_by_key_for_one_result(fake_get):
    calls = fake_get(FakeResponse(json_data={"numFound": 1, "docs": [DUNE]}))

    result = openlibrary.fetch_work("OL893414W")

    params = calls[0]["params"]
    assert params["q"] == "key:/works/OL893414W"
    assert params["limit"] == 1
    assert params["fields"] == openlibrary.FIELDS
    assert result.work_id == "OL893414W"
    assert result.title == "Dune"
    assert len(result.isbns) == 10


@pytest.mark.parametrize(
    "docs", [[], [{**DUNE, "key": "/works/OL1W"}]], ids=["no match", "other work"]
)
def test_fetch_work_raises_when_open_library_has_no_such_work(fake_get, docs):
    fake_get(FakeResponse(json_data={"numFound": len(docs), "docs": docs}))

    with pytest.raises(openlibrary.SearchError, match="no book with that ID"):
        openlibrary.fetch_work("OL893414W")


def test_fetch_work_passes_on_search_failures(fake_get):
    fake_get(FakeResponse(status_code=503))

    with pytest.raises(openlibrary.SearchError, match="HTTP 503"):
        openlibrary.fetch_work("OL893414W")
