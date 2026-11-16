"""Book page owner controls (Phase 9): the edit form and Remove."""

import pytest
from django.urls import reverse

from accounts.models import User
from books import openlibrary
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


def make_user(username):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )


@pytest.fixture(autouse=True)
def open_library_down(monkeypatch):
    """The book page and its owner controls never need Open Library."""

    def down(*args, **kwargs):
        pytest.fail("The book page called the Open Library client.")

    monkeypatch.setattr(openlibrary, "search_books", down)
    monkeypatch.setattr(openlibrary, "fetch_work", down)


@pytest.fixture
def book():
    return Book.objects.create(work_id="OL1W", title="Dune", authors="Frank Herbert")


def test_remove_deletes_only_the_users_own_save(client, book):
    reader, friend = make_user("reader"), make_user("friend")
    own = SavedBook.objects.create(user=reader, book=book, rating=5)
    friends = SavedBook.objects.create(user=friend, book=book, rating=3)
    client.force_login(reader)

    # Someone else's save is "not found", and stays exactly where it was.
    response = client.post(reverse("books:remove_saved_book", args=[friends.pk]))
    assert response.status_code == 404
    assert SavedBook.objects.filter(pk=friends.pk).exists()

    response = client.post(reverse("books:remove_saved_book", args=[own.pk]))
    assert response.status_code == 302
    assert not SavedBook.objects.filter(pk=own.pk).exists()
    # The Book row and the other user's save are untouched.
    assert Book.objects.filter(pk=book.pk).exists()
    assert SavedBook.objects.filter(pk=friends.pk).exists()

    # The book page still works and now offers to save it again.
    page = client.get(response.url)
    html = page.content.decode()
    assert page.status_code == 200
    assert "Save to my library" in html
    assert "3.0 ★ from 1 rating" in html


def test_logged_out_remove_redirects_to_sign_in(client, book):
    save = SavedBook.objects.create(user=make_user("reader"), book=book)

    response = client.post(reverse("books:remove_saved_book", args=[save.pk]))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    assert SavedBook.objects.filter(pk=save.pk).exists()


def test_remove_only_accepts_post(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(user=reader, book=book)
    client.force_login(reader)

    response = client.get(reverse("books:remove_saved_book", args=[save.pk]))

    assert response.status_code == 405
    assert SavedBook.objects.filter(pk=save.pk).exists()


# --- Which controls the book page shows ---------------------------------------


def book_page(client, book):
    response = client.get(reverse("books:book_detail", args=[book.work_id]))
    assert response.status_code == 200
    return response.content.decode()


def test_owner_sees_edit_form_and_remove(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(
        user=reader, book=book, status=SavedBook.Status.READING, rating=4
    )
    client.force_login(reader)

    html = book_page(client, book)

    assert 'data-testid="owner-edit-form"' in html
    assert reverse("books:update_saved_book", args=[save.pk]) in html
    assert reverse("books:remove_saved_book", args=[save.pk]) in html
    assert '<option value="reading" selected>' in html
    assert '<option value="4" selected>' in html
    assert 'data-testid="save-button"' not in html


def test_non_owner_sees_no_edit_controls(client, book):
    SavedBook.objects.create(user=make_user("friend"), book=book, rating=3)
    client.force_login(make_user("reader"))

    html = book_page(client, book)

    assert 'data-testid="owner-edit-form"' not in html
    assert 'data-testid="remove"' not in html
    assert "Save to my library" in html


def test_htmx_save_on_the_book_page_shows_the_owner_controls(client, book):
    reader = make_user("reader")
    client.force_login(reader)

    response = client.post(
        reverse("books:save_book", args=[book.work_id]),
        {"source": "book_page"},
        headers={"HX-Request": "true"},
    )

    save = SavedBook.objects.get(user=reader, book=book)
    html = response.content.decode()
    assert 'data-testid="owner-edit-form"' in html
    assert reverse("books:update_saved_book", args=[save.pk]) in html


# --- Editing from the book page ----------------------------------------------


def edit(client, save, data, **kwargs):
    return client.post(
        reverse("books:update_saved_book", args=[save.pk]),
        {"source": "book_page", **data},
        **kwargs,
    )


def test_htmx_edit_returns_only_the_owner_controls(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(user=reader, book=book)
    client.force_login(reader)

    response = edit(
        client,
        save,
        {"status": "read", "rating": "5", "is_public": ["false", "true"]},
        headers={"HX-Request": "true"},
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert html.lstrip().startswith('<div id="owner-controls"')
    assert "<html" not in html
    assert 'data-testid="saved-flash"' in html
    assert 'data-testid="saved-book"' not in html  # not the Saved Books card
    save.refresh_from_db()
    assert (save.status, save.rating, save.is_public) == ("read", 5, True)


def test_book_page_edit_sends_the_new_community_average_out_of_band(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(user=reader, book=book, rating=2)
    SavedBook.objects.create(user=make_user("friend"), book=book, rating=5)
    client.force_login(reader)

    response = edit(client, save, {"rating": "4"}, headers={"HX-Request": "true"})

    html = response.content.decode()
    assert 'id="community-rating"' in html
    assert 'hx-swap-oob="true"' in html
    assert "4.5 ★ from 2 ratings" in html  # (4 + 5) / 2, not the old 3.5
    assert "friend" not in html


def test_saved_books_card_edit_sends_no_community_average(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(user=reader, book=book, rating=2)
    client.force_login(reader)

    response = client.post(
        reverse("books:update_saved_book", args=[save.pk]),
        {"rating": "4"},
        headers={"HX-Request": "true"},
    )

    assert 'id="community-rating"' not in response.content.decode()


def test_invalid_book_page_edit_shows_errors_and_changes_nothing(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(user=reader, book=book, rating=2)
    client.force_login(reader)

    response = edit(
        client, save, {"rating": "9", "status": "read"}, headers={"HX-Request": "true"}
    )

    html = response.content.decode()
    assert 'data-testid="owner-controls"' in html
    assert 'data-testid="edit-errors"' in html
    save.refresh_from_db()
    assert (save.status, save.rating) == (SavedBook.Status.WANT_TO_READ, 2)


def test_book_page_edit_without_javascript_returns_to_the_book_page(client, book):
    reader = make_user("reader")
    save = SavedBook.objects.create(user=reader, book=book)
    client.force_login(reader)

    # A posted `next` is ignored for book page edits.
    response = edit(client, save, {"rating": "3", "next": "/saved/?status=read"})

    assert response.status_code == 302
    assert response.url == book.get_absolute_url()
    save.refresh_from_db()
    assert save.rating == 3


def test_book_page_edit_of_someone_elses_save_is_not_found(client, book):
    save = SavedBook.objects.create(user=make_user("friend"), book=book, rating=3)
    client.force_login(make_user("reader"))

    response = edit(client, save, {"rating": "1"}, headers={"HX-Request": "true"})

    assert response.status_code == 404
    save.refresh_from_db()
    assert save.rating == 3
