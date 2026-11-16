"""`services.update_saved_book`, the one place save edits are validated.

The website's card (and later the book page and the API) all go through it,
so it accepts both form strings and JSON-style values.
"""

import pytest

from accounts.models import User
from books import services
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


@pytest.fixture
def save():
    user = User.objects.create_user(username="u", email="u@example.com", password="x")
    book = Book.objects.create(work_id="OL1W", title="Dune")
    return SavedBook.objects.create(user=user, book=book, rating=3)


def test_json_style_values_are_accepted(save):
    services.update_saved_book(save, {"rating": None, "is_public": True})

    save.refresh_from_db()
    assert save.rating is None
    assert save.is_public is True


def test_integer_rating_is_accepted(save):
    services.update_saved_book(save, {"rating": 5})

    save.refresh_from_db()
    assert save.rating == 5


def test_every_invalid_field_gets_its_own_error(save):
    with pytest.raises(services.InvalidUpdate) as caught:
        services.update_saved_book(
            save, {"status": "dnf", "rating": 7, "is_public": "maybe"}
        )

    assert set(caught.value.errors) == {"status", "rating", "is_public"}


def test_rejected_update_leaves_the_object_in_memory_unchanged(save):
    with pytest.raises(services.InvalidUpdate):
        services.update_saved_book(save, {"rating": 1, "status": "dnf"})

    assert save.rating == 3
    assert save.status == SavedBook.Status.WANT_TO_READ


def test_empty_data_changes_nothing(save):
    services.update_saved_book(save, {})

    save.refresh_from_db()
    assert save.rating == 3
