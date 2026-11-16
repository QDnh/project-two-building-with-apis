"""The Saved Books list (Phase 6).

Saved Books reads only the local database, so these tests fake every Open
Library client function as down to prove the page never needs it.
"""

import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from books import openlibrary
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db

URL = reverse("books:saved_books")


def make_user(username):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


def make_book(n, **fields):
    return Book.objects.create(work_id=f"OL{n}W", title=f"Book {n}", **fields)


@pytest.fixture
def reader():
    return make_user("reader")


@pytest.fixture
def signed_in(client, reader):
    client.force_login(reader)
    return client


@pytest.fixture(autouse=True)
def open_library_down(monkeypatch):
    """Any client call fails the test: Saved Books must not use Open Library."""

    def down(*args, **kwargs):
        pytest.fail("Saved Books called the Open Library client.")

    monkeypatch.setattr(openlibrary, "search_books", down)
    monkeypatch.setattr(openlibrary, "fetch_work", down)


def save_many(user, count):
    """Save `count` books, the first one saved longest ago."""
    now = timezone.now()
    for n in range(1, count + 1):
        save = SavedBook.objects.create(user=user, book=make_book(n))
        # auto_now_add ignores passed values, so set the date afterwards.
        SavedBook.objects.filter(pk=save.pk).update(
            saved_at=now - timedelta(minutes=count - n)
        )


def titles(html):
    return re.findall(r'class="link link-hover">([^<]+)</a>', html)


def get_html(client, **params):
    response = client.get(URL, params)
    assert response.status_code == 200
    return response.content.decode()


def test_logged_out_visitor_is_redirected_to_sign_in(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={URL}"


def test_only_the_users_own_saves_appear(signed_in, reader):
    mine = make_book(1, authors="Frank Herbert")
    theirs = make_book(2)
    SavedBook.objects.create(user=reader, book=mine)
    SavedBook.objects.create(user=make_user("other"), book=theirs, is_public=True)

    html = get_html(signed_in)

    assert titles(html) == ["Book 1"]
    assert "Book 2" not in html


def test_saves_are_listed_newest_first(signed_in, reader):
    save_many(reader, 3)

    assert titles(get_html(signed_in)) == ["Book 3", "Book 2", "Book 1"]


def test_card_shows_book_details_rating_status_and_visibility(signed_in, reader):
    book = make_book(
        893414, authors="Frank Herbert; Brian Herbert", first_publish_year=1965
    )
    SavedBook.objects.create(
        user=reader,
        book=book,
        rating=4,
        status=SavedBook.Status.READING,
        is_public=True,
    )

    html = get_html(signed_in)

    assert f'href="{book.get_absolute_url()}"' in html
    assert "Frank Herbert, Brian Herbert · 1965" in html
    assert "★★★★☆" in html
    assert "Rated 4 out of 5" in html
    assert re.search(r'data-testid="status">\s*Reading\s*<', html)
    assert re.search(r'data-testid="visibility">\s*Public\s*<', html)


def test_unrated_private_save_says_so(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1))

    html = get_html(signed_in)

    assert "Not rated" in html
    assert re.search(r'data-testid="status">\s*Want to read\s*<', html)
    assert re.search(r'data-testid="visibility">\s*Private\s*<', html)
    assert 'data-testid="cover-placeholder"' in html


def test_twelve_saves_per_page_with_page_status(signed_in, reader):
    save_many(reader, 13)

    first = get_html(signed_in)
    second = get_html(signed_in, page=2)

    assert len(titles(first)) == 12
    assert "Page 1 of 2" in first
    assert f'href="{URL}?page=2"' in first
    assert 'data-testid="prev-page"' not in first
    assert titles(second) == ["Book 1"]
    assert "Page 2 of 2" in second
    assert f'href="{URL}?page=1"' in second
    assert 'data-testid="next-page"' not in second


def test_twelve_saves_fit_on_one_page_without_pagination(signed_in, reader):
    save_many(reader, 12)

    html = get_html(signed_in)

    assert len(titles(html)) == 12
    assert 'data-testid="page-status"' not in html


@pytest.mark.parametrize(("page", "expected"), [("abc", 1), ("0", 2), ("99", 2)])
def test_invalid_or_out_of_range_page_shows_a_real_page(
    signed_in, reader, page, expected
):
    save_many(reader, 13)

    html = get_html(signed_in, page=page)

    assert f"Page {expected} of 2" in html


def test_empty_state_for_a_user_with_no_saves(signed_in):
    html = get_html(signed_in)

    assert 'data-testid="no-saves"' in html
    assert f'href="{reverse("books:search_catalog")}"' in html
    assert 'data-testid="page-status"' not in html


def test_htmx_paging_returns_only_the_list_partial(signed_in, reader):
    save_many(reader, 13)

    response = signed_in.get(URL, {"page": "2"}, HTTP_HX_REQUEST="true")

    html = response.content.decode()
    assert "<html" not in html
    assert titles(html) == ["Book 1"]
    assert 'hx-target="#saved-books-list"' in html


@pytest.mark.parametrize("headers", [{}, {"HTTP_HX_REQUEST": "true"}])
def test_responses_vary_on_hx_request_so_back_never_shows_a_bare_partial(
    signed_in, headers
):
    # Without this the browser can cache the HTMX partial for ?page=2 and
    # show it, unstyled, when the user goes back to that URL.
    response = signed_in.get(URL, {"page": "2"}, **headers)

    assert "HX-Request" in response.headers["Vary"]


def test_htmx_history_restore_gets_the_full_page(signed_in, reader):
    save_many(reader, 13)

    response = signed_in.get(
        URL,
        {"page": "2"},
        HTTP_HX_REQUEST="true",
        HTTP_HX_HISTORY_RESTORE_REQUEST="true",
    )

    html = response.content.decode()
    assert "<html" in html
    assert 'id="saved-books-list"' in html


# --- Search, filters and sort (Phase 7) ---------------------------------------


def test_filters_in_the_url_narrow_the_list(signed_in, reader):
    SavedBook.objects.create(
        user=reader, book=make_book(1, authors="Ursula K. Le Guin"), rating=5
    )
    SavedBook.objects.create(
        user=reader, book=make_book(2, authors="Ursula K. Le Guin"), rating=None
    )
    SavedBook.objects.create(user=reader, book=make_book(3), rating=5)

    html = get_html(signed_in, q="le guin", rating="5")

    assert titles(html) == ["Book 1"]
    assert "1 saved book matches these filters" in html


def test_toolbar_shows_the_current_settings(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1))

    html = get_html(
        signed_in,
        q="dune",
        status="reading",
        rating="unrated",
        visibility="private",
        sort="year",
    )

    assert 'data-testid="filter-toolbar"' in html
    assert 'name="q" value="dune"' in html
    assert '<option value="reading" selected>' in html
    assert '<option value="unrated" selected>' in html
    assert '<option value="private" selected>' in html
    assert '<option value="year" selected>' in html

    clear = re.search(
        r'<a href="([^"]+)"[^>]*data-testid="clear-filters-toolbar"', html
    )
    assert clear and clear.group(1) == URL


def test_toolbar_defaults_to_recently_saved(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1))

    html = get_html(signed_in)

    assert '<option value="-saved" selected>' in html


def test_sort_from_the_url_orders_the_list(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1), rating=2)
    SavedBook.objects.create(user=reader, book=make_book(2), rating=5)
    SavedBook.objects.create(user=reader, book=make_book(3))

    assert titles(get_html(signed_in, sort="-rating")) == [
        "Book 2",
        "Book 1",
        "Book 3",
    ]


def test_invalid_values_in_the_url_show_the_normal_list(signed_in, reader):
    save_many(reader, 2)

    html = get_html(
        signed_in, status="bogus", rating="abc", visibility="x", sort="nope"
    )

    assert titles(html) == ["Book 2", "Book 1"]
    assert '<option value="" selected>' not in html  # nothing junk is selected
    assert '<option value="-saved" selected>' in html


def test_pagination_links_keep_the_current_settings(signed_in, reader):
    save_many(reader, 13)

    html = get_html(signed_in, q="book", sort="title", status="", page="1")

    assert f'href="{URL}?q=book&amp;sort=title&amp;page=2"' in html


def test_htmx_filter_request_returns_the_list_and_pushes_a_tidy_url(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1), is_public=True)
    SavedBook.objects.create(user=reader, book=make_book(2))

    # A toolbar submit sends every field, including the empty ones.
    response = signed_in.get(
        URL,
        {"q": "", "status": "", "rating": "", "visibility": "public", "sort": "-saved"},
        HTTP_HX_REQUEST="true",
    )

    html = response.content.decode()
    assert "<html" not in html
    assert 'data-testid="filter-toolbar"' not in html
    assert titles(html) == ["Book 1"]
    assert response.headers["HX-Push-Url"] == f"{URL}?visibility=public"


def test_htmx_paging_pushes_the_page_with_the_settings(signed_in, reader):
    save_many(reader, 13)

    response = signed_in.get(
        URL, {"sort": "title", "page": "2"}, HTTP_HX_REQUEST="true"
    )

    assert response.headers["HX-Push-Url"] == f"{URL}?sort=title&page=2"


def test_htmx_request_with_no_settings_pushes_the_bare_url(signed_in, reader):
    response = signed_in.get(URL, {"status": ""}, HTTP_HX_REQUEST="true")

    assert response.headers["HX-Push-Url"] == URL


def test_full_page_and_history_restore_do_not_push_a_url(signed_in):
    full = signed_in.get(URL, {"status": "read"})
    restore = signed_in.get(
        URL,
        {"status": "read"},
        HTTP_HX_REQUEST="true",
        HTTP_HX_HISTORY_RESTORE_REQUEST="true",
    )

    assert "HX-Push-Url" not in full.headers
    assert "HX-Push-Url" not in restore.headers


def test_no_matches_shows_a_clear_filters_link(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1))

    html = get_html(signed_in, status="read")

    assert 'data-testid="no-matches"' in html
    assert "No saved books match these filters." in html
    assert re.search(rf'href="{URL}"[^>]*data-testid="clear-filters"', html), (
        "clear-filters link should point at the unfiltered list"
    )
    assert 'data-testid="no-saves"' not in html


def test_no_matches_htmx_partial_also_has_the_clear_link(signed_in, reader):
    SavedBook.objects.create(user=reader, book=make_book(1))

    response = signed_in.get(URL, {"q": "zzz"}, HTTP_HX_REQUEST="true")

    assert 'data-testid="clear-filters"' in response.content.decode()


def test_user_with_no_saves_sees_the_empty_state_even_with_filters(signed_in):
    html = get_html(signed_in, status="read")

    assert 'data-testid="no-saves"' in html
    assert 'data-testid="no-matches"' not in html


def test_toolbar_always_has_a_clear_filters_link(signed_in):
    # HTMX swaps only the list, so the toolbar can't show or hide this as
    # filters change; it's always there and always resets to the bare list.
    html = get_html(signed_in)

    assert re.search(rf'<a href="{URL}"[^>]*data-testid="clear-filters-toolbar"', html)
