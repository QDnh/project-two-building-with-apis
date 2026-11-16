"""The Saved Books search, filter and sort function (Phase 7).

`services.filter_saved_books` holds every rule; these tests call it directly
with query-parameter dicts, the way the view passes `request.GET`.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from books import services
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


@pytest.fixture
def reader():
    return User.objects.create_user(
        username="reader", email="reader@example.com", password="x"
    )


_next_id = iter(range(1, 10_000))


def save(user, title, *, authors="", minutes_ago=0, **fields):
    """Save a new book for `user`, saved `minutes_ago` minutes in the past."""
    book = Book.objects.create(
        work_id=f"OL{next(_next_id)}W",
        title=title,
        authors=authors,
        first_publish_year=fields.pop("year", None),
    )
    saved = SavedBook.objects.create(user=user, book=book, **fields)
    SavedBook.objects.filter(pk=saved.pk).update(
        saved_at=timezone.now() - timedelta(minutes=minutes_ago)
    )
    return saved


def titles(user, **params):
    result = services.filter_saved_books(SavedBook.objects.filter(user=user), params)
    return [s.book.title for s in result.saves]


def test_search_matches_title_or_author_ignoring_case(reader):
    save(reader, "Dune", authors="Frank Herbert", minutes_ago=3)
    save(reader, "The Hobbit", authors="J. R. R. Tolkien", minutes_ago=2)
    save(reader, "Herbert West", authors="H. P. Lovecraft", minutes_ago=1)
    save(reader, "Co-written", authors="Ann Smith; BRIAN HERBERT", minutes_ago=0)

    assert titles(reader, q="  herbert ") == ["Co-written", "Herbert West", "Dune"]


def test_rating_sort_puts_highest_first_and_unrated_last(reader):
    # Unrated saves are the newest, so they'd lead if nulls weren't pushed last.
    save(reader, "Unrated B", minutes_ago=0)
    save(reader, "Unrated A", minutes_ago=1)
    save(reader, "Three Z", rating=3, minutes_ago=2)
    save(reader, "One", rating=1, minutes_ago=3)
    save(reader, "Five", rating=5, minutes_ago=4)
    save(reader, "Three A", rating=3, minutes_ago=5)

    assert titles(reader, sort="-rating") == [
        "Five",
        "Three A",
        "Three Z",
        "One",
        "Unrated A",
        "Unrated B",
    ]


@pytest.mark.parametrize(
    ("params", "expected_titles", "expected_filters"),
    [
        # Every value is junk: the default list, nothing recorded as applied.
        (
            {"status": "bogus", "rating": "9", "visibility": "maybe", "sort": "x"},
            ["A", "B", "C", "D"],
            {},
        ),
        # One junk value is dropped; the valid one beside it still applies.
        ({"status": "bogus", "rating": "4"}, ["A"], {"rating": "4"}),
        ({"status": "read", "rating": "abc"}, ["A", "C"], {"status": "read"}),
        (
            {"rating": "unrated", "visibility": "maybe"},
            ["B", "C"],
            {"rating": "unrated"},
        ),
        (
            {"visibility": "public", "rating": "0", "sort": "nope"},
            ["A", "C"],
            {"visibility": "public"},
        ),
    ],
)
def test_invalid_values_are_ignored_and_valid_ones_still_apply(
    reader, params, expected_titles, expected_filters
):
    save(reader, "A", status="read", rating=4, is_public=True, minutes_ago=0)
    save(reader, "B", status="reading", minutes_ago=1)
    save(reader, "C", status="read", is_public=True, minutes_ago=2)
    save(reader, "D", status="want_to_read", rating=2, minutes_ago=3)

    result = services.filter_saved_books(SavedBook.objects.filter(user=reader), params)

    assert [s.book.title for s in result.saves] == expected_titles
    assert result.filters == expected_filters


def test_default_sort_is_recently_saved(reader):
    save(reader, "Old", minutes_ago=2)
    save(reader, "New", minutes_ago=0)
    save(reader, "Middle", minutes_ago=1)

    assert titles(reader) == ["New", "Middle", "Old"]
    assert titles(reader, sort="-saved") == ["New", "Middle", "Old"]


def test_title_sort_is_a_to_z_ignoring_case(reader):
    save(reader, "dune", minutes_ago=0)
    save(reader, "Anathem", minutes_ago=1)
    save(reader, "Babel", minutes_ago=2)

    assert titles(reader, sort="title") == ["Anathem", "Babel", "dune"]


def test_year_sort_is_oldest_first_with_unknown_years_last(reader):
    save(reader, "Unknown", minutes_ago=0)
    save(reader, "Modern", year=2001, minutes_ago=1)
    save(reader, "Classic", year=1813, minutes_ago=2)
    save(reader, "Also 2001", year=2001, minutes_ago=3)

    assert titles(reader, sort="year") == ["Classic", "Also 2001", "Modern", "Unknown"]


@pytest.mark.parametrize(
    ("status", "expected"),
    [("want_to_read", ["Want"]), ("reading", ["Reading"]), ("read", ["Read"])],
)
def test_status_filter(reader, status, expected):
    save(reader, "Want", status="want_to_read")
    save(reader, "Reading", status="reading")
    save(reader, "Read", status="read")

    assert titles(reader, status=status) == expected


@pytest.mark.parametrize(
    ("rating", "expected"), [("5", ["Five"]), ("1", ["One"]), ("unrated", ["None"])]
)
def test_rating_filter(reader, rating, expected):
    save(reader, "Five", rating=5)
    save(reader, "One", rating=1)
    save(reader, "None")

    assert titles(reader, rating=rating) == expected


@pytest.mark.parametrize(
    ("visibility", "expected"), [("public", ["Shared"]), ("private", ["Mine"])]
)
def test_visibility_filter(reader, visibility, expected):
    save(reader, "Shared", is_public=True)
    save(reader, "Mine")

    assert titles(reader, visibility=visibility) == expected


def test_search_filters_and_sort_combine(reader):
    save(reader, "Le Guin: Dispossessed", status="read", rating=5, is_public=True)
    save(reader, "Le Guin: Earthsea", status="read", rating=3, is_public=True)
    save(reader, "Le Guin: Lathe", status="read", rating=4, is_public=False)
    save(reader, "Le Guin: Left Hand", status="reading", is_public=True)
    save(reader, "Other: Dune", status="read", rating=5, is_public=True)

    result = services.filter_saved_books(
        SavedBook.objects.filter(user=reader),
        {"q": "le guin", "status": "read", "visibility": "public", "sort": "title"},
    )

    assert [s.book.title for s in result.saves] == [
        "Le Guin: Dispossessed",
        "Le Guin: Earthsea",
    ]
    assert result.filters == {
        "q": "le guin",
        "status": "read",
        "visibility": "public",
        "sort": "title",
    }


def test_only_the_given_saves_are_filtered(reader):
    other = User.objects.create_user(
        username="other", email="other@example.com", password="x"
    )
    save(reader, "Mine", is_public=True)
    save(other, "Theirs", is_public=True)

    assert titles(reader, visibility="public") == ["Mine"]
