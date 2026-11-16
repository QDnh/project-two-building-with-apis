"""Book and SavedBook models: constraints and the community average (Phase 2)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import User
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


@pytest.fixture
def book():
    return Book.objects.create(
        work_id="OL893414W", title="Dune", authors="Frank Herbert"
    )


def make_user(n):
    return User.objects.create_user(
        username=f"reader{n}", email=f"reader{n}@example.com", password="x"
    )


# --- Community average ------------------------------------------------------


@pytest.mark.parametrize(
    ("ratings", "expected_average", "expected_count"),
    [
        ([5, 4, 4], Decimal("4.3"), 3),  # 4.333… rounds down
        ([5, 4, 4, 4], Decimal("4.3"), 4),  # 4.25 rounds half up, not to even
        ([2], Decimal("2.0"), 1),
        ([], None, 0),
    ],
)
def test_community_rating_averages_every_rating_and_ignores_unrated(
    book, ratings, expected_average, expected_count
):
    # Alternate public and private saves: both count toward the average.
    for n, rating in enumerate(ratings):
        SavedBook.objects.create(
            user=make_user(n), book=book, rating=rating, is_public=n % 2 == 0
        )
    # Unrated saves are ignored.
    SavedBook.objects.create(user=make_user(98), book=book, rating=None)
    # Ratings of other books are ignored.
    other = Book.objects.create(work_id="OL1W", title="Other")
    SavedBook.objects.create(user=make_user(99), book=other, rating=1)

    result = book.community_rating()

    assert result.average == expected_average
    assert result.count == expected_count


# --- Rating constraint ------------------------------------------------------


@pytest.mark.parametrize(
    ("rating", "allowed"),
    [(None, True), (1, True), (5, True), (0, False), (6, False)],
)
def test_database_allows_only_empty_or_1_to_5_ratings(book, rating, allowed):
    # objects.create skips model validators, so only the database decides here.
    def save():
        with transaction.atomic():
            SavedBook.objects.create(user=make_user(1), book=book, rating=rating)

    if allowed:
        save()
        assert SavedBook.objects.get().rating == rating
    else:
        with pytest.raises(IntegrityError):
            save()
        assert not SavedBook.objects.exists()


# --- Other model rules ------------------------------------------------------


@pytest.mark.parametrize("rating", [0, 6])
def test_validators_reject_ratings_outside_1_to_5(book, rating):
    saved = SavedBook(user=make_user(1), book=book, rating=rating)

    with pytest.raises(ValidationError) as excinfo:
        saved.full_clean()

    assert "rating" in excinfo.value.message_dict


def test_a_user_cannot_save_the_same_book_twice(book):
    user = make_user(1)
    SavedBook.objects.create(user=user, book=book)

    with pytest.raises(IntegrityError), transaction.atomic():
        SavedBook.objects.create(user=user, book=book)

    # A different user can still save it.
    SavedBook.objects.create(user=make_user(2), book=book)
    assert book.saves.count() == 2


def test_deleting_a_saved_book_is_blocked(book):
    SavedBook.objects.create(user=make_user(1), book=book, is_public=False)

    with pytest.raises(ProtectedError):
        book.delete()

    assert Book.objects.filter(pk=book.pk).exists()


def test_an_unsaved_book_can_be_deleted(book):
    book.delete()

    assert not Book.objects.exists()


def test_new_saves_default_to_private_want_to_read_and_unrated(book):
    saved = SavedBook.objects.create(user=make_user(1), book=book)

    assert saved.is_public is False
    assert saved.status == SavedBook.Status.WANT_TO_READ
    assert saved.rating is None


def test_isbns_and_subjects_are_capped_at_ten_values():
    book = Book.objects.create(
        work_id="OL2W",
        title="Big",
        isbns=[str(n) for n in range(25)],
        subjects=[f"s{n}" for n in range(25)],
    )
    book.refresh_from_db()

    assert book.isbns == [str(n) for n in range(10)]
    assert book.subjects == [f"s{n}" for n in range(10)]


def test_authors_split_into_a_list():
    book = Book(authors="Terry Pratchett; Neil Gaiman")

    assert book.author_list == ["Terry Pratchett", "Neil Gaiman"]
    assert Book(authors="").author_list == []


def test_cover_url_uses_the_cover_id():
    assert Book(cover_id=123).cover_url() == (
        "https://covers.openlibrary.org/b/id/123-M.jpg"
    )
    assert Book(cover_id=None).cover_url() is None


@pytest.mark.parametrize("work_id", ["OL893414W", "OL1W"])
def test_work_id_accepts_the_short_form(work_id):
    Book(work_id=work_id, title="T").full_clean()


@pytest.mark.parametrize("work_id", ["/works/OL893414W", "OL893414M", "893414"])
def test_work_id_rejects_other_forms(work_id):
    with pytest.raises(ValidationError):
        Book(work_id=work_id, title="T").full_clean()


def test_deleting_a_user_removes_their_saves_but_keeps_the_books(book):
    leaving = make_user(1)
    staying = make_user(2)
    SavedBook.objects.create(user=leaving, book=book, rating=1, is_public=True)
    SavedBook.objects.create(user=staying, book=book, rating=5)
    only_theirs = Book.objects.create(work_id="OL3W", title="Only theirs")
    SavedBook.objects.create(user=leaving, book=only_theirs, rating=2)

    leaving.delete()

    assert not SavedBook.objects.filter(user_id=leaving.pk).exists()
    # Books stay, including one nobody else had saved.
    assert set(Book.objects.values_list("work_id", flat=True)) == {
        "OL893414W",
        "OL3W",
    }
    # Their ratings drop out of the community average.
    assert book.community_rating() == (Decimal("5.0"), 1)
    assert only_theirs.community_rating() == (None, 0)
    # Other users' saves are untouched.
    assert staying.saved_books.get().rating == 5
