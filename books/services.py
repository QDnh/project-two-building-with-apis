"""Shared book logic used by both the website and the API."""

import re
from typing import NamedTuple

from django.db import IntegrityError, transaction
from django.db.models import F, Q, QuerySet
from django.db.models.functions import Lower

from . import openlibrary
from .models import AUTHOR_SEPARATOR, WORK_ID_PATTERN, Book, SavedBook


class InvalidWorkId(ValueError):
    """The work ID isn't in Open Library's short form (e.g. OL893414W)."""


class AlreadySaved(Exception):
    """The user already has this book in their Saved Books."""

    def __init__(self, saved_book):
        super().__init__("This book is already in your Saved Books.")
        self.saved_book = saved_book


def save_book(user, work_id):
    """Save the work with this Open Library ID to the user's Saved Books.

    A Book already in the database is reused with no call to Open Library, so
    saving it keeps working while Open Library is down. A book new to the app
    is looked up on Open Library by its ID; its details only ever come from
    there, never from the caller. The new save is private, "Want to read" and
    unrated.

    Raises InvalidWorkId for a malformed ID (before any request is made),
    AlreadySaved if the user already has the book, and openlibrary.SearchError
    when a new book can't be fetched.
    """
    if not isinstance(work_id, str) or not re.fullmatch(WORK_ID_PATTERN, work_id):
        raise InvalidWorkId(work_id)

    existing = SavedBook.objects.filter(user=user, book__work_id=work_id).first()
    if existing is not None:
        raise AlreadySaved(existing)

    book = Book.objects.filter(work_id=work_id).first()
    if book is None:
        book = create_book_from_open_library(work_id)
    try:
        with transaction.atomic():
            return SavedBook.objects.create(user=user, book=book)
    except IntegrityError:
        # Saved twice at the same moment (e.g. a double click).
        raise AlreadySaved(SavedBook.objects.get(user=user, book=book)) from None


# Fields an owner can edit on a save, as the website and the API send them.
EDITABLE_FIELDS = ("status", "rating", "is_public")


class InvalidUpdate(ValueError):
    """One or more edited values are invalid; nothing was saved."""

    def __init__(self, errors):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


TRUE_VALUES = {True, "true", "on", "1"}
FALSE_VALUES = {False, "false", "off", "0"}


def update_saved_book(save, data):
    """Apply any subset of status, rating and is_public from `data` to `save`.

    `data` is a form's POST data or any dict. Only keys present in `data`
    change; an empty or None rating clears it ("Not rated"). Every value is
    checked before anything changes: if any is invalid, InvalidUpdate is
    raised with an error per field and the save is left exactly as it was.
    Returns the save.
    """
    changes, errors = {}, {}
    if "status" in data:
        status = data["status"]
        if status in SavedBook.Status.values:
            changes["status"] = status
        else:
            errors["status"] = "Choose Want to read, Reading or Read."
    if "rating" in data:
        rating = data["rating"]
        if rating in ("", None):
            changes["rating"] = None
        elif str(rating) in RATING_VALUES:
            changes["rating"] = int(rating)
        else:
            errors["rating"] = "Rating must be a whole number of stars from 1 to 5."
    if "is_public" in data:
        value = data["is_public"]
        # Only booleans and strings: a JSON list or object isn't hashable.
        if isinstance(value, bool | str) and (
            value in TRUE_VALUES or value in FALSE_VALUES
        ):
            changes["is_public"] = value in TRUE_VALUES
        else:
            errors["is_public"] = "Choose public or private."
    if errors:
        raise InvalidUpdate(errors)
    for field, value in changes.items():
        setattr(save, field, value)
    if changes:
        save.save(update_fields=list(changes))
    return save


# Saved Books filter values accepted from the URL; anything else is ignored.
UNRATED = "unrated"
RATING_VALUES = {"1", "2", "3", "4", "5"}
VISIBILITY_VALUES = {"public", "private"}

# Saved Books sort options: URL value → (label, ordering). Ties fall back to a
# stable order so paging never shows a save twice or skips one.
DEFAULT_SORT = "-saved"
SAVED_BOOK_SORTS = {
    "-saved": ("Recently saved", ["-saved_at", "-pk"]),
    "title": ("Title A–Z", [Lower("book__title"), "-pk"]),
    "year": (
        "First published",
        [
            F("book__first_publish_year").asc(nulls_last=True),
            Lower("book__title"),
            "-pk",
        ],
    ),
    "-rating": (
        "My rating",
        [F("rating").desc(nulls_last=True), Lower("book__title"), "-pk"],
    ),
}


class FilteredSaves(NamedTuple):
    """Saves after search, filters and sort, plus the settings that applied."""

    saves: QuerySet
    filters: dict


def filter_saved_books(saves, params):
    """Apply Saved Books search, filters and sort from the query parameters.

    Every Saved Books list rule lives here. `params` is `request.GET` or any
    dict of strings:
      q           title or author contains this text, ignoring case
      status      one of SavedBook.Status
      rating      "1"–"5", or "unrated"
      visibility  "public" or "private"
      sort        a key of SAVED_BOOK_SORTS (default: recently saved)

    Missing, empty or invalid values are ignored, never an error. Returns the
    filtered, sorted saves plus `filters`: only the settings that applied, in
    a fixed order, for building URLs and showing the toolbar.
    """
    filters = {}
    query = (params.get("q") or "").strip()
    if query:
        filters["q"] = query
        saves = saves.filter(
            Q(book__title__icontains=query) | Q(book__authors__icontains=query)
        )

    status = params.get("status")
    if status in SavedBook.Status.values:
        filters["status"] = status
        saves = saves.filter(status=status)

    rating = params.get("rating")
    if rating == UNRATED:
        filters["rating"] = rating
        saves = saves.filter(rating__isnull=True)
    elif rating in RATING_VALUES:
        filters["rating"] = rating
        saves = saves.filter(rating=int(rating))

    visibility = params.get("visibility")
    if visibility in VISIBILITY_VALUES:
        filters["visibility"] = visibility
        saves = saves.filter(is_public=visibility == "public")

    sort = params.get("sort")
    if sort in SAVED_BOOK_SORTS and sort != DEFAULT_SORT:
        filters["sort"] = sort
    else:
        sort = DEFAULT_SORT
    return FilteredSaves(
        saves=saves.order_by(*SAVED_BOOK_SORTS[sort][1]), filters=filters
    )


def create_book_from_open_library(work_id):
    """Fetch a work from Open Library and store it as a Book."""
    result = openlibrary.fetch_work(work_id)
    book, _ = Book.objects.get_or_create(
        work_id=result.work_id,
        defaults={
            "title": result.title,
            "authors": AUTHOR_SEPARATOR.join(result.authors),
            "first_publish_year": result.first_publish_year,
            "cover_id": result.cover_id,
            "edition_count": result.edition_count,
            # Book.save() caps both lists at MAX_LIST_VALUES.
            "isbns": result.isbns,
            "subjects": result.subjects,
        },
    )
    return book
