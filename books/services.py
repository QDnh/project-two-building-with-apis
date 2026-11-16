"""Shared book logic used by both the website and the API."""

import re

from django.db import IntegrityError, transaction

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
