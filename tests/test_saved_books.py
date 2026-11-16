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
