"""The prune_books management command (Phase 11)."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


@pytest.fixture
def library():
    """Three books: one saved publicly, one saved privately, one unsaved."""
    reader = User.objects.create_user(
        username="reader", email="reader@example.com", password="x"
    )
    public = Book.objects.create(work_id="OL1W", title="Publicly saved")
    private = Book.objects.create(work_id="OL2W", title="Privately saved")
    unsaved = Book.objects.create(work_id="OL3W", title="Nobody saved")
    SavedBook.objects.create(user=reader, book=public, is_public=True)
    SavedBook.objects.create(user=reader, book=private, is_public=False)
    return {"public": public, "private": private, "unsaved": unsaved}


def prune(*args):
    out = StringIO()
    call_command("prune_books", *args, stdout=out)
    return out.getvalue()


def remaining_work_ids():
    return set(Book.objects.values_list("work_id", flat=True))


def test_dry_run_lists_unsaved_books_and_deletes_nothing(library):
    output = prune("--dry-run")

    assert "OL3W" in output and "Nobody saved" in output
    assert "OL1W" not in output and "OL2W" not in output
    assert "Nothing was deleted" in output
    assert remaining_work_ids() == {"OL1W", "OL2W", "OL3W"}


def test_prune_deletes_only_books_nobody_has_saved(library):
    output = prune()

    assert "Deleted 1 unsaved book(s)" in output
    # Saved books survive whether the save is public or private.
    assert remaining_work_ids() == {"OL1W", "OL2W"}
    assert SavedBook.objects.count() == 2


def test_pruned_books_404_on_the_book_page_and_api(client, library):
    prune()

    assert client.get(reverse("books:book_detail", args=["OL3W"])).status_code == 404
    api = APIClient()
    assert api.get(reverse("api:book", args=["OL3W"])).status_code == 404
    # A surviving book still works.
    assert client.get(reverse("books:book_detail", args=["OL1W"])).status_code == 200


def test_a_book_becomes_prunable_once_its_last_save_is_removed(library):
    SavedBook.objects.filter(book=library["private"]).delete()

    prune()

    assert remaining_work_ids() == {"OL1W"}


def test_prune_with_nothing_to_delete_says_so(library):
    library["unsaved"].delete()

    output = prune()

    assert "No unsaved books to prune" in output
    assert remaining_work_ids() == {"OL1W", "OL2W"}
