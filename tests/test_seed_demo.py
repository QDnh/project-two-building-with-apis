"""The seed_demo management command (Phase 2)."""

from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.core.management import CommandError, call_command

from accounts.models import User
from books.management.commands.seed_demo import DEMO_PASSWORD, DEMO_SAVES
from books.models import Book, SavedBook

pytestmark = pytest.mark.django_db


@pytest.fixture
def debug_on(settings):
    # pytest-django turns DEBUG off for tests; the command needs it on.
    settings.DEBUG = True


def seed():
    out = StringIO()
    call_command("seed_demo", stdout=out)
    return out.getvalue()


def counts():
    return User.objects.count(), Book.objects.count(), SavedBook.objects.count()


# The autouse network guard in conftest.py fails any of these tests if the
# command tries to reach Open Library.


def test_seed_loads_demo_users_books_and_saves(debug_on):
    output = seed()

    expected_saves = sum(len(saves) for saves in DEMO_SAVES.values())
    assert counts() == (len(DEMO_SAVES), 15, expected_saves)
    assert "Demo data ready" in output
    dune = Book.objects.get(work_id="OL893414W")
    assert dune.title == "Dune"
    assert dune.author_list == ["Frank Herbert"]
    assert dune.cover_id and dune.isbns and dune.subjects


def test_demo_users_can_sign_in_with_the_documented_password(debug_on):
    seed()

    for username in DEMO_SAVES:
        assert authenticate(username=username, password=DEMO_PASSWORD)


def test_seed_creates_a_mix_of_statuses_ratings_and_visibility(debug_on):
    seed()
    saves = SavedBook.objects.all()

    assert {s.status for s in saves} == set(SavedBook.Status.values)
    assert {s.is_public for s in saves} == {True, False}
    assert saves.filter(rating__isnull=True).exists()
    assert saves.filter(rating__isnull=False).exists()
    # At least one demo user shares nothing, to show the empty profile.
    assert any(
        not SavedBook.objects.filter(user__username=u, is_public=True).exists()
        for u in DEMO_SAVES
    )


def test_running_seed_twice_does_not_create_duplicates(debug_on):
    seed()
    first = counts()
    # Changes made while demoing are reset on the next run.
    alice_dune = SavedBook.objects.get(
        user__username="alice", book__work_id="OL893414W"
    )
    alice_dune.rating = 1
    alice_dune.save()

    seed()

    assert counts() == first
    alice_dune.refresh_from_db()
    assert alice_dune.rating == 5


def test_seed_refuses_to_run_when_debug_is_off(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="DEBUG"):
        seed()

    assert counts() == (0, 0, 0)


def test_seed_does_not_use_the_open_library_client(debug_on, monkeypatch):
    # Belt and braces on top of the socket guard: any HTTP call fails loudly.
    def no_http(*args, **kwargs):
        raise AssertionError("seed_demo must not make HTTP requests")

    monkeypatch.setattr("requests.get", no_http)
    monkeypatch.setattr("requests.Session.request", no_http)

    seed()

    assert Book.objects.count() == 15
