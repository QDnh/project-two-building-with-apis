"""Saving a book by its Open Library work ID (Phase 5).

These tests fake the Open Library client's `fetch_work` function, so no HTTP
request is ever built.
"""

import logging

import pytest
from django.urls import reverse

from accounts.models import User
from books import openlibrary
from books.models import Book, SavedBook
from books.openlibrary import SearchError, SearchResult
from books.services import AlreadySaved, InvalidWorkId, save_book

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="reader", email="reader@example.com", password="x"
    )


@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace fetch_work. Call with a SearchResult or an exception to use."""
    calls = []

    def install(result):
        def fake(work_id, **kwargs):
            calls.append(work_id)
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(openlibrary, "fetch_work", fake)
        return calls

    return install


def test_book_already_in_the_database_saves_while_open_library_is_down(
    user, fake_fetch
):
    calls = fake_fetch(SearchError("Open Library is unavailable right now."))
    book = Book.objects.create(work_id="OL893414W", title="Dune")

    save_book(user, "OL893414W")

    assert SavedBook.objects.filter(user=user, book=book).exists()
    assert calls == []
    assert Book.objects.count() == 1


def test_new_book_is_fetched_from_open_library_and_saved_with_safe_defaults(
    user, fake_fetch
):
    calls = fake_fetch(
        SearchResult(
            work_id="OL893414W",
            title="Dune",
            authors=["Frank Herbert", "Brian Herbert"],
            first_publish_year=1965,
            cover_id=11481354,
            edition_count=12,
            isbns=[f"97804410135{n:02d}" for n in range(12)],
            subjects=["Science fiction", "Arrakis"],
        )
    )

    saved = save_book(user, "OL893414W")

    assert calls == ["OL893414W"]
    book = Book.objects.get(work_id="OL893414W")
    assert book.title == "Dune"
    assert book.author_list == ["Frank Herbert", "Brian Herbert"]
    assert book.first_publish_year == 1965
    assert book.cover_id == 11481354
    assert book.edition_count == 12
    assert book.isbns == [f"97804410135{n:02d}" for n in range(10)]
    assert book.subjects == ["Science fiction", "Arrakis"]
    # New saves are private, "Want to read" and unrated.
    assert saved.book == book
    assert saved.user == user
    assert saved.is_public is False
    assert saved.status == SavedBook.Status.WANT_TO_READ
    assert saved.rating is None


# --- The save view ----------------------------------------------------------


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client


def post_save(client, work_id, **data):
    return client.post(
        reverse("books:save_book", args=[work_id]), data, HTTP_HX_REQUEST="true"
    )


def test_failed_save_of_a_new_book_shows_an_alert_next_to_the_button(
    signed_in, fake_fetch
):
    message = "Open Library is unavailable right now (HTTP 503). Try again later."
    fake_fetch(SearchError(message))

    response = post_save(signed_in, "OL893414W")
    html = response.content.decode()

    assert response.status_code == 200
    assert "<html" not in html  # only the save control is swapped
    assert 'data-testid="save-error"' in html
    assert message in html
    assert "Your saved books are still available" in html
    assert f'href="{reverse("books:saved_books")}"' in html
    assert 'data-testid="save-button"' in html  # still there to try again
    assert not SavedBook.objects.exists()
    assert not Book.objects.exists()


# --- More save-function rules -----------------------------------------------

DUNE = SearchResult(work_id="OL893414W", title="Dune", authors=["Frank Herbert"])


def test_saving_a_book_twice_raises_already_saved_without_a_request(user, fake_fetch):
    calls = fake_fetch(DUNE)
    first = save_book(user, "OL893414W")

    with pytest.raises(AlreadySaved) as caught:
        save_book(user, "OL893414W")

    assert caught.value.saved_book == first
    assert calls == ["OL893414W"]  # only the first save asked Open Library
    assert SavedBook.objects.count() == 1


def test_another_user_saving_the_same_book_reuses_the_stored_book(user, fake_fetch):
    calls = fake_fetch(DUNE)
    other = User.objects.create_user(
        username="friend", email="friend@example.com", password="x"
    )
    save_book(user, "OL893414W")

    save_book(other, "OL893414W")

    assert calls == ["OL893414W"]
    assert Book.objects.count() == 1
    assert SavedBook.objects.count() == 2


@pytest.mark.parametrize(
    "work_id", ["", "dune", "OL893414M", "/works/OL893414W", "OL1W OR title:x"]
)
def test_malformed_work_id_is_rejected_before_any_request(user, fake_fetch, work_id):
    calls = fake_fetch(DUNE)

    with pytest.raises(InvalidWorkId):
        save_book(user, work_id)

    assert calls == []
    assert not Book.objects.exists()


def test_new_book_failure_creates_nothing(user, fake_fetch):
    fake_fetch(SearchError("Open Library has no book with that ID."))

    with pytest.raises(SearchError):
        save_book(user, "OL893414W")

    assert not Book.objects.exists()
    assert not SavedBook.objects.exists()


# --- More save-view behaviour -----------------------------------------------


def test_successful_htmx_save_shows_saved_link_to_the_book_page(signed_in, fake_fetch):
    fake_fetch(DUNE)

    html = post_save(signed_in, "OL893414W").content.decode()

    assert 'data-testid="saved-link"' in html
    assert "Saved ✓" in html
    assert f'href="{reverse("books:book_detail", args=["OL893414W"])}"' in html
    assert 'data-testid="save-button"' not in html
    assert SavedBook.objects.filter(book__work_id="OL893414W").exists()


def test_book_details_in_the_request_are_ignored(signed_in, fake_fetch):
    fake_fetch(DUNE)

    post_save(
        signed_in,
        "OL893414W",
        title="Hacked title",
        authors="Someone Else",
        cover_id="1",
        isbns="123",
    )

    book = Book.objects.get(work_id="OL893414W")
    assert book.title == "Dune"
    assert book.authors == "Frank Herbert"
    assert book.cover_id is None
    assert book.isbns == []


def test_duplicate_save_says_it_is_already_in_saved_books(signed_in, user, fake_fetch):
    fake_fetch(SearchError("Open Library is down."))
    book = Book.objects.create(work_id="OL893414W", title="Dune")
    SavedBook.objects.create(user=user, book=book)

    html = post_save(signed_in, "OL893414W").content.decode()

    assert 'data-testid="already-saved"' in html
    assert "already in your" in html
    assert 'data-testid="saved-link"' in html
    assert 'data-testid="save-error"' not in html
    assert SavedBook.objects.count() == 1


def test_book_page_save_keeps_its_label_when_it_fails(signed_in, fake_fetch):
    fake_fetch(SearchError("Open Library is down."))

    html = post_save(signed_in, "OL893414W", source="book_page").content.decode()

    assert "Save to my library" in html
    assert 'name="source" value="book_page"' in html


def test_failed_save_is_logged_on_the_server(signed_in, fake_fetch, caplog):
    fake_fetch(SearchError("Could not connect to Open Library."))

    with caplog.at_level(logging.WARNING, logger="books.views"):
        post_save(signed_in, "OL893414W")

    assert "Saving OL893414W failed" in caplog.text
    assert "Could not connect to Open Library." in caplog.text


def test_malformed_work_id_returns_404(signed_in, fake_fetch):
    calls = fake_fetch(DUNE)

    response = post_save(signed_in, "not-a-work")

    assert response.status_code == 404
    assert calls == []


def test_logged_out_save_redirects_to_sign_in_and_saves_nothing(client, fake_fetch):
    calls = fake_fetch(DUNE)

    response = post_save(client, "OL893414W")

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    assert calls == []
    assert not SavedBook.objects.exists()


def test_get_is_not_allowed(signed_in, fake_fetch):
    fake_fetch(DUNE)

    response = signed_in.get(reverse("books:save_book", args=["OL893414W"]))

    assert response.status_code == 405
    assert not SavedBook.objects.exists()


def test_save_without_javascript_redirects_back_with_a_message(signed_in, fake_fetch):
    fake_fetch(DUNE)
    book_page = reverse("books:book_detail", args=["OL893414W"])

    response = signed_in.post(
        reverse("books:save_book", args=["OL893414W"]), {"next": book_page}, follow=True
    )

    assert response.redirect_chain == [(book_page, 302)]
    html = response.content.decode()
    assert "Saved to your Saved Books." in html
    assert 'data-testid="in-saved-books"' in html


def test_failed_save_without_javascript_shows_the_error_after_redirect(
    signed_in, fake_fetch
):
    fake_fetch(SearchError("Open Library is unavailable right now (HTTP 503)."))
    search_url = reverse("books:search_catalog")

    response = signed_in.post(
        reverse("books:save_book", args=["OL893414W"]),
        {"next": search_url},
        follow=True,
    )

    assert response.redirect_chain == [(search_url, 302)]
    html = response.content.decode()
    assert "Open Library is unavailable right now (HTTP 503)." in html
    assert "Your saved books are still available." in html


@pytest.mark.parametrize(
    "next_url", ["https://evil.example.com/", "//evil.example.com"]
)
def test_save_without_javascript_never_redirects_off_site(
    signed_in, fake_fetch, next_url
):
    fake_fetch(DUNE)

    response = signed_in.post(
        reverse("books:save_book", args=["OL893414W"]), {"next": next_url}
    )

    assert response.url == reverse("books:search_catalog")


def test_htmx_save_on_the_book_page_shows_in_saved_books_not_a_self_link(
    signed_in, fake_fetch
):
    fake_fetch(DUNE)

    html = post_save(signed_in, "OL893414W", source="book_page").content.decode()

    assert 'data-testid="in-saved-books"' in html
    assert f'href="{reverse("books:saved_books")}"' in html
    assert 'data-testid="saved-link"' not in html
    assert reverse("books:book_detail", args=["OL893414W"]) not in html
    assert 'data-testid="save-button"' not in html
