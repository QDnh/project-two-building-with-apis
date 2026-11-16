"""The Search Catalog page (Phase 3).

These tests fake the Open Library client's `search_books` function, so no
HTTP request is ever built.
"""

import logging

import pytest
from django.urls import reverse

from accounts.models import User
from books import openlibrary
from books.openlibrary import SearchError, SearchPage, SearchResult

pytestmark = pytest.mark.django_db

URL = reverse("books:search_catalog")

DUNE = SearchResult(
    work_id="OL893414W",
    title="Dune",
    authors=["Frank Herbert"],
    first_publish_year=1965,
    cover_id=11481354,
)
NO_COVER = SearchResult(work_id="OL1W", title="Mystery Book")


@pytest.fixture
def signed_in(client):
    user = User.objects.create_user(
        username="reader", email="reader@example.com", password="x"
    )
    client.force_login(user)
    return client


@pytest.fixture
def fake_search(monkeypatch):
    """Replace search_books. Call with a SearchPage or an exception to use."""
    calls = []

    def install(result):
        def fake(query, **kwargs):
            calls.append({"query": query, **kwargs})
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(openlibrary, "search_books", fake)
        return calls

    return install


def get_html(client, **params):
    response = client.get(URL, params)
    assert response.status_code == 200
    return response.content.decode()


# --- Access -----------------------------------------------------------------


def test_logged_out_visitor_is_redirected_to_sign_in(client, fake_search):
    calls = fake_search(SearchPage(total=0, results=[]))

    response = client.get(URL, {"q": "dune"})

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    assert calls == []


def test_navbar_links_to_search_catalog(signed_in):
    html = signed_in.get(reverse("home")).content.decode()

    assert f'href="{URL}"' in html


# --- Searching --------------------------------------------------------------


def test_page_without_a_query_shows_only_the_form(signed_in, fake_search):
    calls = fake_search(SearchPage(total=0, results=[]))

    html = get_html(signed_in)

    assert 'name="q"' in html
    assert calls == []
    assert 'data-testid="form-error"' not in html


def test_results_show_cover_title_authors_and_year(signed_in, fake_search):
    calls = fake_search(SearchPage(total=1234, results=[DUNE, NO_COVER]))

    html = get_html(signed_in, q="dune")

    assert calls == [{"query": "dune"}]
    assert html.count('data-testid="search-result"') == 2
    assert "Dune" in html
    assert "Frank Herbert" in html
    assert "1965" in html
    assert 'src="https://covers.openlibrary.org/b/id/11481354-L.jpg"' in html
    assert "Unknown author" in html  # the result with no authors
    assert "Showing 2 of 1,234 matches" in html
    # The query is kept in the search box.
    assert 'value="dune"' in html


def test_isbn_with_hyphens_and_spaces_is_sent_cleaned(signed_in, fake_search):
    calls = fake_search(SearchPage(total=1, results=[DUNE]))

    get_html(signed_in, q=" 978-0-441 01359-3 ")

    assert calls[0]["query"] == "9780441013593"


def test_no_results_message(signed_in, fake_search):
    fake_search(SearchPage(total=0, results=[]))

    html = get_html(signed_in, q="asdfghjkl")

    assert "No books found matching" in html
    assert 'data-testid="search-result"' not in html


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_shows_a_message_and_never_calls_the_client(
    signed_in, fake_search, query
):
    calls = fake_search(SearchPage(total=0, results=[]))

    html = get_html(signed_in, q=query)

    assert calls == []
    assert 'data-testid="form-error"' in html
    assert "Enter a title, author, keywords or an ISBN" in html


# --- Open Library failures --------------------------------------------------


def test_failure_shows_alert_with_link_to_saved_books(signed_in, fake_search):
    fake_search(SearchError("Open Library is unavailable right now (HTTP 503)."))

    html = get_html(signed_in, q="dune")

    assert 'data-testid="search-error"' in html
    assert "Open Library is unavailable right now (HTTP 503)." in html
    assert "Your saved books are still available" in html
    assert f'href="{reverse("books:saved_books")}"' in html
    assert 'data-testid="search-result"' not in html


def test_failure_is_logged_on_the_server(signed_in, fake_search, caplog):
    fake_search(SearchError("Could not connect to Open Library."))

    with caplog.at_level(logging.WARNING, logger="books.views"):
        get_html(signed_in, q="dune")

    assert "Open Library search failed" in caplog.text
    assert "Could not connect to Open Library." in caplog.text
