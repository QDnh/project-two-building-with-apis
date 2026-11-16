"""Card quick edits on Saved Books (Phase 8).

One update view edits the owner's save: any subset of status, rating and the
public flag, validated in one place. These tests post to it the way the card
does and check the database and the returned card.
"""

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


@pytest.fixture
def reader():
    return make_user("reader")


@pytest.fixture
def signed_in(client, reader):
    client.force_login(reader)
    return client


@pytest.fixture(autouse=True)
def open_library_down(monkeypatch):
    """Editing a save never needs Open Library."""

    def down(*args, **kwargs):
        pytest.fail("A card edit called the Open Library client.")

    monkeypatch.setattr(openlibrary, "search_books", down)
    monkeypatch.setattr(openlibrary, "fetch_work", down)


@pytest.fixture
def save(reader):
    book = Book.objects.create(work_id="OL1W", title="Dune", authors="Frank Herbert")
    return SavedBook.objects.create(
        user=reader,
        book=book,
        status=SavedBook.Status.READING,
        rating=4,
        is_public=True,
    )


def edit_url(save):
    return reverse("books:update_saved_book", args=[save.pk])


def test_partial_update_changes_only_the_fields_sent(signed_in, save):
    # An empty rating clears it; status and public weren't sent, so they stay.
    signed_in.post(edit_url(save), {"rating": ""}, headers={"HX-Request": "true"})

    save.refresh_from_db()
    assert save.rating is None
    assert save.status == SavedBook.Status.READING
    assert save.is_public is True


def test_invalid_value_rejects_the_whole_update(signed_in, save):
    # The rating is valid but the status isn't, so nothing may be saved.
    signed_in.post(
        edit_url(save),
        {"rating": "2", "status": "finished"},
        headers={"HX-Request": "true"},
    )

    save.refresh_from_db()
    assert save.rating == 4
    assert save.status == SavedBook.Status.READING


def test_card_that_no_longer_matches_the_filters_shows_the_hint(signed_in, save):
    # The list is filtered to "Reading"; marking the book Read means it no
    # longer matches, but the card must come back with the hint, not vanish.
    response = signed_in.post(
        edit_url(save),
        {"status": "read", "next": f"{reverse('books:saved_books')}?status=reading"},
        headers={"HX-Request": "true"},
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-testid="saved-book"' in html
    assert 'data-testid="stale-hint"' in html


HTMX = {"HX-Request": "true"}
SAVED_URL = reverse("books:saved_books")


def test_editing_someone_elses_save_is_not_found(client, save):
    client.force_login(make_user("other"))

    response = client.post(edit_url(save), {"rating": "1"}, headers=HTMX)

    assert response.status_code == 404
    save.refresh_from_db()
    assert save.rating == 4


def test_editing_a_missing_save_is_not_found_like_someone_elses(signed_in):
    response = signed_in.post(
        reverse("books:update_saved_book", args=[999]), {"rating": "1"}
    )

    assert response.status_code == 404


def test_logged_out_edit_redirects_to_sign_in(client, save):
    response = client.post(edit_url(save), {"rating": "1"})

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    save.refresh_from_db()
    assert save.rating == 4


def test_only_post_is_allowed(signed_in, save):
    assert signed_in.get(edit_url(save)).status_code == 405


def test_htmx_response_is_only_the_updated_card_with_saved_flash(signed_in, save):
    response = signed_in.post(
        edit_url(save), {"rating": "2", "next": SAVED_URL}, headers=HTMX
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html
    assert html.count('data-testid="saved-book"') == 1
    assert f'id="saved-book-{save.pk}"' in html
    assert 'data-testid="saved-flash"' in html
    assert "Rated 2 out of 5" in html
    # Unfiltered list: the card still matches, so there's no hint.
    assert 'data-testid="stale-hint"' not in html


def test_card_that_still_matches_the_filters_has_no_hint(signed_in, save):
    response = signed_in.post(
        edit_url(save),
        {"rating": "5", "next": f"{SAVED_URL}?status=reading&sort=title"},
        headers=HTMX,
    )

    assert 'data-testid="stale-hint"' not in response.content.decode()


def test_card_keeps_the_list_url_for_the_next_edit(signed_in, save):
    list_url = f"{SAVED_URL}?status=reading&amp;page=2"
    response = signed_in.post(
        edit_url(save),
        {"rating": "5", "next": f"{SAVED_URL}?status=reading&page=2"},
        headers=HTMX,
    )

    assert f'name="next" value="{list_url}"' in response.content.decode()


def test_status_change_from_the_card(signed_in, save):
    signed_in.post(edit_url(save), {"status": "want_to_read"}, headers=HTMX)

    save.refresh_from_db()
    assert save.status == SavedBook.Status.WANT_TO_READ


def test_public_toggle_ticked_sends_true_after_the_hidden_false(signed_in, save):
    save.is_public = False
    save.save()

    signed_in.post(edit_url(save), {"is_public": ["false", "true"]}, headers=HTMX)

    save.refresh_from_db()
    assert save.is_public is True


def test_public_toggle_unticked_sends_only_the_hidden_false(signed_in, save):
    signed_in.post(edit_url(save), {"is_public": ["false"]}, headers=HTMX)

    save.refresh_from_db()
    assert save.is_public is False


@pytest.mark.parametrize("rating", ["0", "6", "9", "-1", "abc", "2.5"])
def test_out_of_range_or_malformed_rating_is_rejected(signed_in, save, rating):
    response = signed_in.post(edit_url(save), {"rating": rating}, headers=HTMX)

    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-testid="edit-errors"' in html
    assert "1 to 5" in html
    assert 'data-testid="saved-flash"' not in html
    save.refresh_from_db()
    assert save.rating == 4


def test_invalid_public_value_is_rejected(signed_in, save):
    signed_in.post(edit_url(save), {"is_public": "maybe"}, headers=HTMX)

    save.refresh_from_db()
    assert save.is_public is True


def test_without_javascript_the_edit_redirects_back_to_the_list(signed_in, save):
    list_url = f"{SAVED_URL}?status=reading&page=2"

    response = signed_in.post(edit_url(save), {"rating": "1", "next": list_url})

    assert response.status_code == 302
    assert response.url == list_url
    save.refresh_from_db()
    assert save.rating == 1
    page = signed_in.get(SAVED_URL).content.decode()
    assert "Saved “Dune”." in page


def test_without_javascript_an_invalid_edit_shows_the_error(signed_in, save):
    response = signed_in.post(edit_url(save), {"rating": "9"}, follow=True)

    html = response.content.decode()
    assert "1 to 5. Nothing was changed." in html
    save.refresh_from_db()
    assert save.rating == 4


def test_an_offsite_next_url_is_replaced_with_saved_books(signed_in, save):
    response = signed_in.post(
        edit_url(save), {"rating": "1", "next": "https://evil.example/"}
    )

    assert response.url == SAVED_URL


def test_saved_books_cards_post_back_the_current_list_url(signed_in, save):
    html = signed_in.get(SAVED_URL, {"status": "reading", "q": "dune"}).content
    html = html.decode()

    assert f'action="{edit_url(save)}"' in html
    assert f'name="next" value="{SAVED_URL}?q=dune&amp;status=reading"' in html


def test_cards_have_stars_clear_status_and_public_controls(signed_in, save):
    html = signed_in.get(SAVED_URL).content.decode()

    for n in range(1, 6):
        assert f'name="rating" value="{n}"' in html
    assert 'data-testid="clear-rating"' in html
    assert 'name="status"' in html
    assert 'name="is_public" value="true"' in html


def test_unrated_card_has_no_clear_button(signed_in, save):
    save.rating = None
    save.save()

    html = signed_in.get(SAVED_URL).content.decode()

    assert 'data-testid="clear-rating"' not in html
