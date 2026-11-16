"""Tests for scripts/openlibrary_search.py.

These never touch the real internet: each test replaces `requests.get`
with a fake that returns a canned response or raises an error.
"""

import pytest
import requests

import openlibrary_search as ols


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

        monkeypatch.setattr(ols.requests, "get", fake)
        return calls

    return install


@pytest.fixture
def run_main(monkeypatch, capsys):
    """Run main() as if the user typed `typed`; return (exit_code, output)."""
    monkeypatch.setenv("OPENLIBRARY_CONTACT_EMAIL", "test@example.com")

    def run(typed):
        monkeypatch.setattr("builtins.input", lambda prompt: typed)
        exit_code = ols.main()
        return exit_code, capsys.readouterr().out

    return run


def test_successful_search_sends_expected_request(fake_get):
    calls = fake_get(FakeResponse(json_data={"numFound": 1234, "docs": [DUNE]}))

    total, books = ols.search_books("dune", "me@example.com")

    assert total == 1234
    assert books == [DUNE]
    sent = calls[0]
    assert sent["url"] == ols.SEARCH_URL
    assert sent["params"]["q"] == "dune"
    assert sent["params"]["limit"] == 5
    assert sent["timeout"] == ols.TIMEOUT_SECONDS
    assert "me@example.com" in sent["headers"]["User-Agent"]


def test_successful_search_displays_results(fake_get, run_main):
    fake_get(FakeResponse(json_data={"numFound": 1234, "docs": [DUNE]}))

    exit_code, output = run_main("dune")

    assert exit_code == 0
    assert 'Showing 1 of 1,234 matches for "dune"' in output
    assert "1. Dune (1965)" in output
    assert "by Frank Herbert" in output
    assert "ID: OL893414W" in output


def test_no_results(fake_get, run_main):
    fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    exit_code, output = run_main("asdfghjkl")

    assert exit_code == 0
    assert 'No books found matching "asdfghjkl".' in output


def test_empty_input_makes_no_request(fake_get, run_main):
    calls = fake_get(FakeResponse(json_data={"numFound": 0, "docs": []}))

    exit_code, output = run_main("   ")

    assert exit_code == 1
    assert "Please enter a search phrase" in output
    assert calls == []


@pytest.mark.parametrize(
    ("result", "expected_message"),
    [
        (requests.exceptions.ConnectionError(), "Could not connect to Open Library"),
        (requests.exceptions.Timeout(), "did not respond within 10 seconds"),
        (FakeResponse(status_code=503), "unavailable right now (HTTP 503)"),
        (FakeResponse(status_code=429), "too many requests (HTTP 429)"),
        (FakeResponse(status_code=404), "rejected the request (HTTP 404)"),
        (FakeResponse(invalid_json=True), "wasn't valid JSON"),
        (FakeResponse(json_data={"error": "oops"}), "unexpected format"),
    ],
    ids=["connection", "timeout", "503", "429", "404", "bad-json", "bad-shape"],
)
def test_failures_show_specific_message(fake_get, run_main, result, expected_message):
    fake_get(result)

    exit_code, output = run_main("dune")

    assert exit_code == 1
    assert "Error:" in output
    assert expected_message in output


def test_format_book_fills_in_missing_fields():
    text = ols.format_book(3, {})

    assert text == "3. Untitled (year unknown)\n   by Unknown author\n   ID: unknown"
