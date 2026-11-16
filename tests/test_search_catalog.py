"""The Search Catalog page (Phases 3 and 4).

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

    assert calls == [{"query": "dune", "page": 1, "limit": 20}]
    assert html.count('data-testid="search-result"') == 2
    assert "Dune" in html
    assert "Frank Herbert" in html
    assert "1965" in html
    assert 'src="https://covers.openlibrary.org/b/id/11481354-L.jpg"' in html
    assert "Unknown author" in html  # the result with no authors
    assert "Showing 1–2 of 1,234 matches" in html
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


# --- Paging (Phase 4) -------------------------------------------------------


def many_results(total):
    """A full page of 20 results, with `total` matches overall."""
    results = [SearchResult(work_id=f"OL{n}W", title=f"Book {n}") for n in range(20)]
    return SearchPage(total=total, results=results)


@pytest.mark.parametrize(
    ("page_param", "expected_page"),
    [("3", 3), ("1", 1), ("0", 1), ("-2", 1), ("abc", 1), ("", 1)],
)
def test_client_is_called_with_page_and_limit(
    signed_in, fake_search, page_param, expected_page
):
    calls = fake_search(many_results(1000))

    get_html(signed_in, q="dune", page=page_param)

    assert calls == [{"query": "dune", "page": expected_page, "limit": 20}]


def test_summary_shows_the_range_on_later_pages(signed_in, fake_search):
    fake_search(many_results(1000))

    html = get_html(signed_in, q="dune", page="3")

    assert "Showing 41–60 of 1,000 matches" in html
    assert "Page 3 of 10" in html


def test_htmx_request_returns_only_the_results_partial(signed_in, fake_search):
    fake_search(many_results(1000))

    response = signed_in.get(URL, {"q": "dune", "page": "2"}, HTTP_HX_REQUEST="true")
    html = response.content.decode()

    assert response.status_code == 200
    assert html.count('data-testid="search-result"') == 20
    assert "Page 2 of 10" in html
    assert "<html" not in html
    assert 'name="q"' not in html  # no search form, no navbar
    assert 'data-testid="user-menu"' not in html


def test_normal_request_returns_the_full_page(signed_in, fake_search):
    fake_search(many_results(1000))

    html = get_html(signed_in, q="dune", page="2")

    assert "<html" in html
    assert 'name="q"' in html
    assert 'id="search-results"' in html
    assert "Page 2 of 10" in html


def test_htmx_history_restore_returns_the_full_page(signed_in, fake_search):
    fake_search(many_results(1000))

    html = signed_in.get(
        URL,
        {"q": "dune", "page": "2"},
        HTTP_HX_REQUEST="true",
        HTTP_HX_HISTORY_RESTORE_REQUEST="true",
    ).content.decode()

    assert "<html" in html
    assert 'name="q"' in html


def test_pagination_links_keep_the_query_and_use_htmx(signed_in, fake_search):
    fake_search(many_results(1000))

    html = get_html(signed_in, q="le guin", page="2")

    assert f'href="{URL}?q=le+guin&amp;page=1"' in html
    assert f'href="{URL}?q=le+guin&amp;page=3"' in html
    assert f'hx-get="{URL}?q=le+guin&amp;page=3"' in html
    assert 'hx-target="#search-results"' in html
    assert 'hx-push-url="true"' in html


def test_first_page_has_next_but_no_previous(signed_in, fake_search):
    fake_search(many_results(1000))

    html = get_html(signed_in, q="dune")

    assert 'data-testid="prev-page"' not in html
    assert 'data-testid="next-page"' in html


def test_last_page_has_previous_but_no_next(signed_in, fake_search):
    fake_search(many_results(45))  # 3 pages

    html = get_html(signed_in, q="dune", page="3")

    assert "Page 3 of 3" in html
    assert 'data-testid="prev-page"' in html
    assert 'data-testid="next-page"' not in html
    assert 'data-testid="refine-hint"' not in html


def test_single_page_of_results_has_no_pagination(signed_in, fake_search):
    fake_search(SearchPage(total=2, results=[DUNE, NO_COVER]))

    html = get_html(signed_in, q="dune")

    assert 'data-testid="page-status"' not in html
    assert 'data-testid="prev-page"' not in html
    assert 'data-testid="next-page"' not in html


def test_next_is_never_offered_past_page_ten(signed_in, fake_search):
    fake_search(many_results(5000))

    html = get_html(signed_in, q="dune", page="10")

    assert "Page 10 of 10" in html
    assert 'data-testid="next-page"' not in html
    assert 'data-testid="refine-hint"' in html
    assert "Try a more specific search" in html


def test_page_above_ten_is_capped_and_shows_the_hint(signed_in, fake_search):
    calls = fake_search(many_results(5000))

    html = get_html(signed_in, q="dune", page="57")

    assert calls[0]["page"] == 10
    assert "Page 10 of 10" in html
    assert 'data-testid="refine-hint"' in html


def test_page_past_the_last_result_links_back_to_the_first(signed_in, fake_search):
    fake_search(SearchPage(total=30, results=[]))

    html = get_html(signed_in, q="dune", page="5")

    assert 'data-testid="past-last-page"' in html
    assert f'href="{URL}?q=dune&amp;page=1"' in html
    assert "No books found matching" not in html
